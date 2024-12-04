


from googlesearch import search

# to search
query = "Identification of contradictory patterns in experimental datasets for the development of models for electrical cables diagnostics"

for j in search(query, tld="co.in", num=10, stop=10, pause=2):
    print(j)