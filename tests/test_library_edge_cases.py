import copy
import json
import shutil
import subprocess
import sys

import pytest

import admin
import user


@pytest.fixture
def library_data():
    return {
        "library": {"name": "Test Library", "branch": "West", "year": 2030},
        "categories": ["Technology", "History"],
        "books": {
            "K7": {
                "title": "Signal Processing", "author": "Casey Morgan",
                "category": "Technology", "available": True
            },
            "M9": {
                "title": "History of Computing", "author": "Ada Chen",
                "category": "History", "available": False
            },
            "Z2": {
                "title": "Signals and Systems", "author": "Casey Morgan",
                "category": "Technology", "available": True
            }
        },
        "loans": [{"book_id": "M9", "borrower": "Taylor Kim"}]
    }


@pytest.mark.parametrize("query", [" k7 ", " SIGNAL PROCESSING ", " casey MORGAN "])
def test_find_by_id_title_or_author(library_data, query):
    before = copy.deepcopy(library_data)
    assert admin.find_book(library_data["books"], query) == "K7"
    assert library_data == before


def test_book_id_takes_priority_over_a_matching_title(library_data):
    library_data["books"]["K7"]["title"] = "M9"
    assert admin.find_book(library_data["books"], "M9") == "M9"


@pytest.mark.parametrize("query", ["", " \t "])
def test_empty_search(library_data, query):
    books = library_data["books"]
    assert admin.find_book(books, query) is None
    assert user.search_by_title(books, query) == []
    assert user.books_in_category(books, query) == []


def test_search_returns_all_matches_without_changing_data(library_data):
    before = copy.deepcopy(library_data)
    books = library_data["books"]
    assert user.search_by_title(books, " SIGNAL ") == ["K7", "Z2"]
    assert user.books_in_category(books, " TECHNOLOGY ") == ["K7", "Z2"]
    assert user.search_by_title(books, "Not present") == []
    assert library_data == before


def test_borrow_by_title_and_keep_borrower_capitalization(library_data):
    books, loans = library_data["books"], library_data["loans"]
    assert user.borrow_book(books, loans, "signal processing", "  Evan McKay  ") == "OK"
    assert books["K7"]["available"] is False
    assert loans == [
        {"book_id": "M9", "borrower": "Taylor Kim"},
        {"book_id": "K7", "borrower": "Evan McKay"}
    ]
    assert admin.library_statistics(books) == (3, 1, 2)


@pytest.mark.parametrize("query,borrower,expected", [
    ("UNKNOWN", "Taylor Kim", "BOOK_NOT_FOUND"),
    ("M9", " \t ", "EMPTY_NAME"),
    ("M9", "Wrong Person", "NOT_ON_LOAN"),
    ("K7", "Taylor Kim", "NOT_ON_LOAN")
])
def test_failed_return_leaves_data_unchanged(library_data, query, borrower, expected):
    before = copy.deepcopy(library_data)
    assert user.return_book(library_data["books"], library_data["loans"], query, borrower) == expected
    assert library_data == before


def test_return_removes_only_the_matching_loan(library_data):
    books, loans = library_data["books"], library_data["loans"]
    assert user.borrow_book(books, loans, "K7", "Another Reader") == "OK"
    assert user.return_book(books, loans, " HISTORY OF COMPUTING ", " tAYLOR kIM ") == "OK"
    assert books["M9"]["available"] is True
    assert books["K7"]["available"] is False
    assert loans == [{"book_id": "K7", "borrower": "Another Reader"}]


def test_existing_loan_blocks_borrowing_when_flag_is_inconsistent(library_data):
    books, loans = library_data["books"], library_data["loans"]
    books["M9"]["available"] = True
    before = copy.deepcopy(library_data)
    assert user.borrow_book(books, loans, "M9", "New Reader") == "NOT_AVAILABLE"
    assert library_data == before
    assert user.return_book(books, loans, "M9", "Taylor Kim") == "OK"
    assert books["M9"]["available"] is True
    assert loans == []


def test_unavailable_book_without_a_loan_is_not_changed(library_data):
    books, loans = library_data["books"], library_data["loans"]
    books["K7"]["available"] = False
    before = copy.deepcopy(library_data)
    assert user.borrow_book(books, loans, "K7", "Reader") == "NOT_AVAILABLE"
    assert user.return_book(books, loans, "K7", "Reader") == "NOT_ON_LOAN"
    assert library_data == before


def test_remaining_loan_keeps_book_unavailable(library_data):
    books, loans = library_data["books"], library_data["loans"]
    loans.append({"book_id": "M9", "borrower": "Other Reader"})
    assert user.return_book(books, loans, "M9", "Taylor Kim") == "OK"
    assert books["M9"]["available"] is False
    assert loans == [{"book_id": "M9", "borrower": "Other Reader"}]


def test_displays_include_required_fields(library_data, capsys):
    before = copy.deepcopy(library_data)
    assert admin.display_books(library_data["books"]) is None
    assert admin.display_loans(library_data["loans"], library_data["books"]) is None
    output = capsys.readouterr().out
    assert "BOOK CATALOGUE" in output
    assert "K7 | Signal Processing | Technology | AVAILABLE" in output
    assert "M9 | History of Computing | History | ON LOAN" in output
    assert "CURRENT LOANS" in output
    assert "M9 | History of Computing | Borrower: Taylor Kim" in output
    assert library_data == before


def test_empty_library(capsys):
    assert admin.library_statistics({}) == (0, 0, 0)
    assert admin.find_book({}, "K7") is None
    assert user.search_by_title({}, "signal") == []
    assert user.books_in_category({}, "Technology") == []
    assert admin.display_books({}) is None
    assert admin.display_loans([], {}) is None
    output = capsys.readouterr().out
    assert "BOOK CATALOGUE" in output
    assert "CURRENT LOANS" in output


def test_json_round_trip_unicode_and_overwrite(library_data, tmp_path):
    library_data["library"]["name"] = "\u56fe\u4e66\u9986"
    library_data["books"]["K7"]["title"] = "\u6570\u636e\u7ed3\u6784"
    filename = tmp_path / "library.json"
    assert admin.save_library(library_data, filename) is None
    assert admin.load_library(filename) == library_data
    assert "\u56fe\u4e66\u9986" in filename.read_text(encoding="utf-8")
    library_data["books"] = {}
    library_data["loans"] = []
    admin.save_library(library_data, filename)
    assert admin.load_library(filename) == library_data


def test_invalid_json_reports_the_error(tmp_path):
    filename = tmp_path / "invalid.json"
    filename.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        admin.load_library(filename)
    with pytest.raises(FileNotFoundError):
        admin.load_library(tmp_path / "missing.json")


@pytest.fixture
def cli_project(library_data, tmp_path):
    app_dir = tmp_path / "application"
    app_dir.mkdir()
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    shutil.copy2(admin.__file__, app_dir / "admin.py")
    shutil.copy2(user.__file__, app_dir / "user.py")
    admin.save_library(library_data, app_dir / "library.json")
    return app_dir, outside_dir


def test_admin_reads_data_beside_script_from_another_directory(cli_project):
    app_dir, outside_dir = cli_project
    before = (app_dir / "library.json").read_bytes()
    result = subprocess.run(
        [sys.executable, "-B", str(app_dir / "admin.py")], cwd=outside_dir,
        capture_output=True, text=True, timeout=5, check=True
    )
    assert "LIBRARY ADMINISTRATION" in result.stdout
    assert "Library: Test Library" in result.stdout
    assert "LIBRARY STATISTICS" in result.stdout
    assert "Total books: 3" in result.stdout
    assert "Available: 2" in result.stdout
    assert "Borrowed: 1" in result.stdout
    assert (app_dir / "library.json").read_bytes() == before


def test_menu_search_borrow_return_save_and_restart(cli_project):
    app_dir, outside_dir = cli_project
    command = [sys.executable, "-B", str(app_dir / "user.py")]
    result = subprocess.run(
        command, cwd=outside_dir, capture_output=True, text=True, timeout=5, check=True,
        input="9\n1\n SIGNAL \n2\n technology \n3\n k7 \nNew Reader\n4\nM9\ntaylor kim\n5\n"
    )
    assert "Invalid selection" in result.stdout
    assert "Signal Processing" in result.stdout
    assert "Signals and Systems" in result.stdout
    assert "Book borrowed successfully." in result.stdout
    assert "Book returned successfully." in result.stdout
    assert "Library data saved." in result.stdout
    saved = admin.load_library(app_dir / "library.json")
    assert saved["books"]["K7"]["available"] is False
    assert saved["books"]["M9"]["available"] is True
    assert saved["loans"] == [{"book_id": "K7", "borrower": "New Reader"}]

    subprocess.run(
        command, cwd=outside_dir, capture_output=True, text=True, timeout=5, check=True,
        input="4\nsignal processing\nnew reader\n5\n"
    )
    reloaded = admin.load_library(app_dir / "library.json")
    assert reloaded["books"]["K7"]["available"] is True
    assert reloaded["loans"] == []


@pytest.mark.parametrize("choice,query,name,message", [
    ("3", "missing", "Reader", "Book not found."),
    ("3", "K7", "   ", "Borrower name cannot be empty."),
    ("3", "M9", "Reader", "This book is not available for borrowing."),
    ("4", "M9", "Wrong Reader", "No matching loan was found for this borrower.")
])
def test_menu_errors_leave_saved_records_unchanged(cli_project, choice, query, name, message):
    app_dir, outside_dir = cli_project
    before = admin.load_library(app_dir / "library.json")
    result = subprocess.run(
        [sys.executable, "-B", str(app_dir / "user.py")], cwd=outside_dir,
        input=f"{choice}\n{query}\n{name}\n5\n",
        capture_output=True, text=True, timeout=5, check=True
    )
    assert message in result.stdout
    assert admin.load_library(app_dir / "library.json") == before
