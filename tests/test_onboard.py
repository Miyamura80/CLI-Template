import onboard
from tests.test_template import TestTemplate


class TestOnboard(TestTemplate):
    def test_build_rename_replacements_keeps_raw_description_for_general_files(self):
        replacements = onboard._build_rename_replacements(
            name="my-tool",
            description='My "awesome" tool',
            github_owner="new-owner",
            github_repo="new-repo",
            current_name="old-tool",
            current_desc="Old description",
            current_owner="old-owner",
            current_repo="old-repo",
        )

        assert ("Old description", 'My "awesome" tool') in replacements

    def test_update_pyproject_description_escapes_quotes(self, tmp_path, monkeypatch):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('name = "my-tool"\ndescription = "My "awesome" tool"\n')
        monkeypatch.setattr(onboard, "PROJECT_ROOT", tmp_path)

        changed_files: list[str] = []
        onboard._update_pyproject_description('My "awesome" tool', changed_files)

        assert pyproject.read_text() == 'name = "my-tool"\ndescription = "My \\"awesome\\" tool"\n'
        assert changed_files == ["pyproject.toml"]

    def test_update_pyproject_description_preserves_backslash_sequences(
        self, tmp_path, monkeypatch
    ):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('name = "my-tool"\ndescription = "Old description"\n')
        monkeypatch.setattr(onboard, "PROJECT_ROOT", tmp_path)

        changed_files: list[str] = []
        onboard._update_pyproject_description(r'path\1 tool', changed_files)

        assert pyproject.read_text() == 'name = "my-tool"\ndescription = "path\\1 tool"\n'
        assert changed_files == ["pyproject.toml"]

    def test_read_pyproject_description_handles_escaped_quotes(self, tmp_path, monkeypatch):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('name = "my-tool"\n[project]\ndescription = "My \\"awesome\\" tool"\n')
        monkeypatch.setattr(onboard, "PROJECT_ROOT", tmp_path)

        assert onboard._read_pyproject_description() == 'My "awesome" tool'
