## This module contains the user interface for the library system. 
# It allows users to search for books, borrow books, and return books.

## Import the necessary functions from the admin module. 
# Replace "function_name1" with the actual function names you want to import.

from admin import (
    load_library,
    save_library,
    find_book,
    display_books
)
from pathlib import Path



## Search books by category.
## This function should return book IDs that match the given category.
def books_in_category(
    books,
    category
):
    category = category.strip().casefold()
    matches = []
    if not category:
        return matches
    for book_id, book in books.items():
        if book["category"].strip().casefold() == category:
            matches.append(book_id)
    return matches

    


## Search books by full or partial title.
## This function should return book IDs that match the given title or part of the title.
def search_by_title(
    books,
    search_text
):
    search = search_text.strip().casefold()
    matches = []
    if not search:
        return matches
    for book_id, book in books.items():
        if search in book["title"].casefold():
            matches.append(book_id)
    return matches
    


## Create logic to let users borrow books.
## The function should check if the book is available or on loan, or if the borrower name is provided.
## If the book is not found, then return "BOOK_NOT_FOUND"
## If the borrower name is empty, then return "EMPTY_NAME"
## If the book is not available, then return "NOT_AVAILABLE"
## If the book is successfully borrowed, then return "OK"
def borrow_book(
    books,
    loans,
    search_text,
    borrower
):
    book_id = find_book(books, search_text)
    if book_id is None:
        return "BOOK_NOT_FOUND"

    name = borrower.strip()
    if not name:
        return "EMPTY_NAME"

    if not books[book_id]["available"]:
        return "NOT_AVAILABLE"
    # An existing loan still blocks borrowing if the availability flag is wrong.
    if any(loan["book_id"] == book_id for loan in loans):
        return "NOT_AVAILABLE"

    loans.append({"book_id": book_id, "borrower": name})
    books[book_id]["available"] = False
    return "OK"

    


## Create logic to let users return books.
## The function should check if the book is on loan, or if the borrower name is provided
## If the book is not found, then return "BOOK_NOT_FOUND"
## If the borrower name is empty, then return "EMPTY_NAME"
## If the book is not on loan, then return "NOT_ON_LOAN"
## If the book is successfully returned, then return "OK"

def return_book(
    books,
    loans,
    book_title,
    borrower
):
    book_id = find_book(books, book_title)
    if book_id is None:
        return "BOOK_NOT_FOUND"

    name = borrower.strip().casefold()
    if not name:
        return "EMPTY_NAME"

    for index, loan in enumerate(loans):
        if (loan["book_id"] == book_id
                and loan["borrower"].strip().casefold() == name):
            loans.pop(index)
            books[book_id]["available"] = not any(
                other["book_id"] == book_id for other in loans
            )
            return "OK"
    return "NOT_ON_LOAN"

    



## The main function that runs the user interface for the library system.
## The function must first load the library data from a JSON file, then display a menu for the user to select options.
## The options include searching for books by title or category, borrowing a book, returning a book, and exiting the program.
## When the user selects an option, the corresponding function is called to perform the action.
## The program continues to display the menu until the user chooses to exit, at which point the library data is saved back to the JSON file.
## The main function should also handle invalid selections by displaying an error message and prompting the user to select again.
def main():
    filename = Path(__file__).with_name("library.json")
    data = load_library(filename)
    books = data["books"]
    loans = data["loans"]
    messages = {
        "BOOK_NOT_FOUND": "Book not found.",
        "EMPTY_NAME": "Borrower name cannot be empty.",
        "NOT_AVAILABLE": "This book is not available for borrowing.",
        "NOT_ON_LOAN": "No matching loan was found for this borrower."
    }

    while True:
        print("\nLIBRARY USER SYSTEM")
        print("=" * 60)
        print("1. Search by title")
        print("2. Search by category")
        print("3. Borrow a book")
        print("4. Return a book")
        print("5. Save and exit")
        choice = input("Select an option (1-5): ").strip()

        if choice in ("1", "2"):
            if choice == "1":
                matches = search_by_title(books, input("Title or part of title: "))
            else:
                matches = books_in_category(books, input("Category: "))
            display_books({book_id: books[book_id] for book_id in matches})
        elif choice in ("3", "4"):
            search_text = input("Book ID, full title or author: ")
            borrower = input("Borrower name: ")
            if choice == "3":
                result = borrow_book(books, loans, search_text, borrower)
            else:
                result = return_book(books, loans, search_text, borrower)
            if result == "OK":
                if choice == "3":
                    print("Book borrowed successfully.")
                else:
                    print("Book returned successfully.")
            else:
                print(messages[result])
        elif choice == "5":
            save_library(data, filename)
            print("Library data saved. Goodbye.")
            break
        else:
            print("Invalid selection. Please choose a number from 1 to 5.")


if __name__ == "__main__":
    main()

