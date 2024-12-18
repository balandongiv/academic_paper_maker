Here is a Python code that uses Flask for creating a web dashboard/UI. This dashboard allows you to:

Show text data.
Navigate through rows of a Pandas DataFrame (Next/Previous functionality).
Accept text input from the user.
Display specific column information.
Accept JSON input and update the DataFrame.
Include an Exit button to shut down the server.
supports displaying PDFs stored as file paths or attachments in the Pandas DataFrame.
the PDF is displayed on the right side of the page, with the data and controls on the left side. For testing, both rows in the DataFrame now point to the same PDF file path.
To save annotations or highlights made by the user on the PDF when they click Next or Previous, you need to manage the annotations explicitly

allow to search by column name and show it in the dashboard
allow to received input from user and update the dataframe. if the column is not availaible, create a new column
generate a python code that


Here is a Python code that uses Flask for creating a web dashboard/UI. This dashboard allows you to:

Show text data.
Navigate through rows of a Pandas DataFrame (Next/Previous functionality).
Accept text input from the user.
Display specific column information.
Accept JSON input and update the DataFrame.
Include an Exit button to shut down the server.
upports displaying PDFs stored as file paths or attachments in the Pandas DataFrame.
the PDF is displayed on the right side of the page, with the data and controls on the left side. For testing, both rows in the DataFrame now point to the same PDF file path.
To save annotations or highlights made by the user on the PDF when they click Next or Previous, you need to manage the annotations explicitly>

The mockup data as follow

dpath = r'C:\Users\balan\IdeaProjects\academic_paper_maker\ragpdf\data\test3.pdf'

# Sample DataFrame with PDF paths
data = {
'ID': [1, 2],
'Name': ['Alice', 'Bob'],
'pdf_path': [dpath, dpath]  # Using the same PDF for testing
}