"""
Автотесты совместимости Git с SELECTOS.
Запуск: pytest -v
"""

import os
import re
import subprocess
import pytest


def run(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def git(args, cwd=None):
    return run(["git"] + args, cwd=cwd)


@pytest.fixture
def repo(tmp_path):
    git(["init", str(tmp_path)])
    git(["config", "user.name", "Tester"], cwd=str(tmp_path))
    git(["config", "user.email", "test@selectos.local"], cwd=str(tmp_path))
    return tmp_path


@pytest.fixture
def repo_with_commit(repo):
    (repo / "base.txt").write_text("base")
    git(["add", "."], cwd=str(repo))
    git(["commit", "-m", "init"], cwd=str(repo))
    return repo


# Установка и версия

def test_git_version():
    """2-3: git --version возвращает строку, версия >= 2."""
    result = run(["git", "--version"])
    assert result.returncode == 0
    assert result.stdout.startswith("git version")
    major = int(re.search(r"git version (\d+)", result.stdout).group(1))
    assert major >= 2


# Базовые операции

def test_init(tmp_path):
    """4: git init создаёт .git."""
    git(["init", str(tmp_path)])
    assert (tmp_path / ".git").exists()


def test_config(repo):
    """5: git config сохраняет и возвращает значения."""
    git(["config", "user.name", "QA"], cwd=str(repo))
    result = git(["config", "user.name"], cwd=str(repo))
    assert result.stdout.strip() == "QA"


def test_commit_and_log(repo):
    """6: add + commit создают коммит, log его показывает."""
    (repo / "file.txt").write_text("hello")
    git(["add", "."], cwd=str(repo))
    result = git(["commit", "-m", "first commit"], cwd=str(repo))
    assert result.returncode == 0
    log = git(["log", "--oneline"], cwd=str(repo))
    assert "first commit" in log.stdout


def test_diff(repo_with_commit):
    """7: git diff показывает изменения."""
    (repo_with_commit / "base.txt").write_text("changed")
    result = git(["diff"], cwd=str(repo_with_commit))
    assert result.returncode == 0
    assert "changed" in result.stdout or "base" in result.stdout


# Ветвление

def test_branch_and_checkout(repo_with_commit):
    """8: создание ветки и переключение."""
    git(["branch", "dev"], cwd=str(repo_with_commit))
    git(["checkout", "dev"], cwd=str(repo_with_commit))
    branches = git(["branch"], cwd=str(repo_with_commit)).stdout
    assert "* dev" in branches


def test_merge(repo_with_commit):
    """9: merge без конфликта."""
    git(["checkout", "-b", "feature"], cwd=str(repo_with_commit))
    (repo_with_commit / "feature.txt").write_text("feature")
    git(["add", "."], cwd=str(repo_with_commit))
    git(["commit", "-m", "feature"], cwd=str(repo_with_commit))
    git(["checkout", "-"], cwd=str(repo_with_commit))
    result = git(["merge", "feature"], cwd=str(repo_with_commit))
    assert result.returncode == 0
    assert (repo_with_commit / "feature.txt").exists()


def test_merge_conflict(repo_with_commit):
    """10: конфликт merge детектируется."""
    f = repo_with_commit / "base.txt"

    git(["checkout", "-b", "branch-a"], cwd=str(repo_with_commit))
    f.write_text("branch-a")
    git(["add", "."], cwd=str(repo_with_commit))
    git(["commit", "-m", "a"], cwd=str(repo_with_commit))

    git(["checkout", "-"], cwd=str(repo_with_commit))
    f.write_text("main-change")
    git(["add", "."], cwd=str(repo_with_commit))
    git(["commit", "-m", "main"], cwd=str(repo_with_commit))

    result = git(["merge", "branch-a"], cwd=str(repo_with_commit))
    assert result.returncode != 0
    assert "<<<<<<<" in f.read_text()


# Теги

def test_tag(repo_with_commit):
    """12: создание и удаление тега."""
    git(["tag", "v1.0"], cwd=str(repo_with_commit))
    assert "v1.0" in git(["tag"], cwd=str(repo_with_commit)).stdout
    git(["tag", "-d", "v1.0"], cwd=str(repo_with_commit))
    assert "v1.0" not in git(["tag"], cwd=str(repo_with_commit)).stdout


# Edge cases

def test_filename_with_spaces(repo):
    """13: файл с пробелами в имени."""
    f = repo / "my file.txt"
    f.write_text("spaces")
    result = git(["add", "my file.txt"], cwd=str(repo))
    assert result.returncode == 0


def test_non_root_user(repo):
    """15: работа от непривилегированного пользователя."""
    if os.geteuid() == 0:
        pytest.skip("запущено от root")
    (repo / "user.txt").write_text("user")
    result = git(["add", "user.txt"], cwd=str(repo))
    assert result.returncode == 0
