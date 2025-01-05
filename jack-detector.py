from fastapi import FastAPI
from fastapi.responses import FileResponse

from main import get_users

app = FastAPI()

tracked_macs = set(map(lambda l: l.split(" ")[0], open("macs.txt").readlines()))
print(tracked_macs)


@app.get("/")
def read_root():
    online_users = get_users()
    if not set(online_users.keys()).isdisjoint(tracked_macs):
        return FileResponse("html/present.html")
    else:
        return FileResponse("html/absent.html")
