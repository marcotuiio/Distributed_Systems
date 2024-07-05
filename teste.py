import pandas as pd

users = [
    {
        "user": "robert@gmail",
        "password": "1234",
        "cookies": "0999"
    },
    {
        "user": "dany@west",
        "password": "9098",
        "cookies": "0114"
    }
]

login = "robert@gmail"
df = pd.DataFrame(users)
# print(df["user"].tolist())

# if login in df["user"].tolist():
matching_row = df.loc[df["user"] == login]
print(matching_row["password"].iloc[0])
if not matching_row.empty:
    print("its here!!")
else:
    print(f"no user with this login <{login}>")

# print(df["user"].iloc[0])