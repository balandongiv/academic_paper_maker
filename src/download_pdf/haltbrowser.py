import tkinter as tk
from tkinter import messagebox


def show_popup():
    """
    Creates a pop-up window asking the user for confirmation.
    """
    root = tk.Tk()
    root.withdraw()
    user_response = messagebox.askokcancel(
        "Confirmation",
        "I'm here so that you login via the institutional login page. Do you want to proceed?"
    )
    root.destroy()
    return user_response