import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from json_compat import loads as json_loads
from tools.import_samaritan_pentateuch import (
    DownloadedDataset,
    download_latest_dataset,
    extract_books,
    import_text_fabric,
    load_features,
    square_to_samaritan,
)


def feature(data: str) -> str:
    return f"@node\n@version=1.0\n\n{data}\n"


class ImportSamaritanPentateuchTests(unittest.TestCase):
    def test_converts_square_letters_and_final_forms_to_samaritan(self):
        self.assertEqual(
            "ࠀࠁࠂࠃࠄࠅࠆࠇࠈࠉࠊࠊࠋࠌࠌࠍࠍࠎࠏࠐࠐࠑࠑࠒࠓࠔࠕ",
            square_to_samaritan("אבגדהוזחטיכךלמםנןסעפףצץקרשת"),
        )

    def test_extracts_verses_from_sign_slots(self):
        features = {
            "book": feature("20\tGenesis"),
            "chapter": feature("21\t1"),
            "verse": feature("22\t1\n2"),
            "oslots": feature("20\t1-9\n1-9\n1-4\n5-9"),
            "sign": feature("\n".join("ברא אלהים")),
        }

        self.assertEqual(
            {"Genesis": {1: {1: "ברא", 2: "אלהים"}}},
            extract_books(features),
        )

    def test_imports_latest_complete_text_fabric_version(self):
        with (
            tempfile.TemporaryDirectory() as source_name,
            tempfile.TemporaryDirectory() as output_name,
        ):
            source = Path(source_name)
            for version in ("1.0", "2.0"):
                version_dir = source / "tf" / version
                version_dir.mkdir(parents=True)
                texts = self._complete_pentateuch_features()
                for name, text in texts.items():
                    version_dir.joinpath(f"{name}.tf").write_text(
                        text, encoding="utf-8"
                    )

            result = import_text_fabric(source, Path(output_name))

            self.assertEqual((5, 5, "2.0"), result)
            version_data = json_loads(
                Path(output_name, "SP", "version.json").read_text(encoding="utf-8")
            )
            genesis_data = json_loads(
                Path(output_name, "SP", "books", "genesis.json").read_text(
                    encoding="utf-8"
                )
            )
            square_version_data = json_loads(
                Path(output_name, "SPSQUARE", "version.json").read_text(
                    encoding="utf-8"
                )
            )
            square_genesis_data = json_loads(
                Path(output_name, "SPSQUARE", "books", "genesis.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                "Samaritan Pentateuch, Samaritan script", version_data["name"]
            )
            self.assertEqual("SMP", version_data["language"])
            self.assertEqual("SMP", square_version_data["language"])
            self.assertEqual("SPSQUARE", square_version_data["code"])
            self.assertEqual(
                "https://doi.org/10.5281/zenodo.7734632",
                genesis_data["source_url"],
            )
            self.assertEqual("ࠀࠁ", genesis_data["chapters"][1]["verses"][1])
            self.assertEqual("אב", square_genesis_data["chapters"][1]["verses"][1])

            loaded, selected_version = load_features(source / "tf" / "2.0")
            self.assertEqual("2.0", selected_version)
            self.assertIn("sign", loaded)

    def test_loads_text_fabric_features_from_zip(self):
        with tempfile.TemporaryDirectory() as directory_name:
            archive_path = Path(directory_name, "sp.zip")
            with ZipFile(archive_path, "w") as archive:
                for name, text in self._complete_pentateuch_features().items():
                    archive.writestr(f"sp/tf/3.0/{name}.tf", text)

            loaded, selected_version = load_features(archive_path)

            self.assertEqual("3.0", selected_version)
            self.assertIn("sign", loaded)

    def test_downloads_latest_zenodo_archive_and_verifies_checksum(self):
        archive_bytes = b"synthetic ZIP contents"
        checksum = hashlib.md5(archive_bytes, usedforsecurity=False).hexdigest()
        metadata = json.dumps(
            {
                "doi_url": "https://doi.org/10.5281/zenodo.12345",
                "metadata": {"version": "v3.0"},
                "files": [
                    {
                        "key": "DT-UCPH/sp-v3.0.zip",
                        "size": len(archive_bytes),
                        "checksum": f"md5:{checksum}",
                        "links": {"self": "https://zenodo.example/sp.zip"},
                    }
                ],
            }
        ).encode()
        doi_response = io.BytesIO()
        doi_response.geturl = lambda: "https://zenodo.org/records/12345"  # type: ignore[attr-defined]

        with tempfile.TemporaryDirectory() as directory_name:
            destination = Path(directory_name, "sp.zip")
            with patch(
                "tools.import_samaritan_pentateuch.urlopen",
                side_effect=(
                    doi_response,
                    io.BytesIO(metadata),
                    io.BytesIO(archive_bytes),
                ),
            ):
                result = download_latest_dataset(destination)

            self.assertEqual(
                DownloadedDataset(
                    "v3.0",
                    len(archive_bytes),
                    "https://doi.org/10.5281/zenodo.12345",
                ),
                result,
            )
            self.assertEqual(archive_bytes, destination.read_bytes())

    def test_uses_supplied_version_doi_for_generated_source_links(self):
        with (
            tempfile.TemporaryDirectory() as source_name,
            tempfile.TemporaryDirectory() as output_name,
        ):
            source = Path(source_name)
            for name, text in self._complete_pentateuch_features().items():
                source.joinpath(f"{name}.tf").write_text(text, encoding="utf-8")

            import_text_fabric(
                source,
                Path(output_name),
                source_url="https://doi.org/10.5281/zenodo.12345",
            )

            genesis_data = json_loads(
                Path(output_name, "SP", "books", "genesis.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                "https://doi.org/10.5281/zenodo.12345",
                genesis_data["source_url"],
            )

    @staticmethod
    def _complete_pentateuch_features() -> dict[str, str]:
        books = ("Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy")
        return {
            "otype": feature("1-10\tsign\n20-24\tbook\n25-29\tchapter\n30-34\tverse"),
            "book": feature("20\t" + "\n".join(books)),
            "chapter": feature("25\t1\n1\n1\n1\n1"),
            "verse": feature("30\t1\n1\n1\n1\n1"),
            "oslots": feature(
                "20\t1-2\n3-4\n5-6\n7-8\n9-10\n"
                "1-2\n3-4\n5-6\n7-8\n9-10\n"
                "1-2\n3-4\n5-6\n7-8\n9-10"
            ),
            "sign": feature("\n".join("אבגדהוזחטי")),
        }


if __name__ == "__main__":
    unittest.main()
