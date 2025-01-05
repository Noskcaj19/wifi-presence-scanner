from fastapi import FastAPI
from fastapi.responses import FileResponse

from main import get_users

app = FastAPI()

tracked_macs = set(map(lambda l: l.split()[0], open("macs.txt").readlines()))
print(tracked_macs)


@app.get("/")
def read_root():
    users = get_users()
    online_users = {m: u for m, u in users.items() if u["Status"] == "on"}
    if not set(online_users.keys()).isdisjoint(tracked_macs):
        return FileResponse("html/present.html")
    return FileResponse("html/absent.html")
