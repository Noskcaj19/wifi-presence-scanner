from datetime import datetime
import sys
import time
from typing import List
from dotenv import load_dotenv
from lxml import etree
from pprint import pprint
import requests

from sqlalchemy import create_engine
from sqlmodel import Field, SQLModel, Session, select

load_dotenv()


def get_users():
    url = "http://192.168.1.254/cgi-bin/devices.ha"
    response = requests.get(url).text
    htmlparser = etree.HTMLParser()
    tree = etree.fromstring(response, htmlparser)
    row_els = tree.xpath(
        "/html/body/div/div[1]/div[1]/div[3]/div[1]/div/div/form/div/table/tr"
    )

    table_rows = []
    my_row = []

    while len(row_els) > 0:
        row_el = row_els.pop(0)
        row_children = row_el.getchildren()
        if len(row_children) <= 1 or row_children[1].text is None:
            continue

        key, val = (
            row_children[0].text.strip().replace("\n", ""),
            row_children[1].text.strip().replace("\n", ""),
        )

        if key == "MAC Address" and len(my_row) > 0:
            table_rows.append(my_row)
            my_row = []

        my_row.append((key, val))

    users = {}
    for row in table_rows:
        users[dict(row)["MAC Address"]] = dict(row)

    return users
    # for mac, user in users.items():
    #     mac = user["MAC Address"]
    #     ip4, name = user["IPv4 Address / Name"].split(" / ")
    #     status = user["Status"]
    # print(f"{name}({mac}) = {status}")


class Mac(SQLModel, table=True):
    mac: str = Field(index=True, default=None, primary_key=True)
    human_name: str = Field(default=None)


class Presence(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    mac: str = Field(index=True)
    startedAt: datetime = Field(default_factory=datetime.now)
    endedAt: datetime | None = Field(index=True)


sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)

SQLModel.metadata.create_all(engine)


def get_tracked_macs(session: Session) -> List[str]:
    return session.exec(select(Mac.mac)).all()


def get_open_sessions(session: Session):
    return session.exec(select(Presence.mac).where(Presence.endedAt.is_(None))).all()


def open_presence(mac: str, session: Session):
    open_session = session.exec(
        select(Presence).where(Presence.mac == mac).where(Presence.endedAt.is_(None))
    ).first()

    if not open_session:
        session.add(Presence(mac=mac))
        print(f"->> adding {mac}")
        session.commit()


def close_presence(mac: str, session: Session):
    open_session = session.exec(
        select(Presence).where(Presence.mac == mac).where(Presence.endedAt.is_(None))
    ).first()
    open_session.endedAt = datetime.now()
    session.add(open_session)
    session.commit()


def process_mac_list(macs: List[str], session: Session):
    for mac in macs:
        open_presence(mac, session)
    all_open_macs = get_open_sessions(session)
    missing_macs = set(all_open_macs).difference(macs)

    for mac in missing_macs:
        print(f"<<- removing {mac}")
        close_presence(mac, session)


def scan():
    users = get_users()
    with Session(engine) as session:
        macs_to_track = get_tracked_macs()
        active_macs = [mac for mac in macs_to_track if mac in users]
        process_mac_list(active_macs, session)


def list_users():
    users = get_users()
    users = {m: u for m, u in users.items() if u["Status"] == "on"}
    if len(sys.argv) > 2 and sys.argv[2] == "less":
        for user in users.values():
            ip4, name = user["IPv4 Address / Name"].split(" / ")
            print(name)
    else:
        pprint(users)


def history():
    with Session(engine) as session:
        pprint(session.exec(select(Presence)).all())


def addmac():
    if len(sys.argv) < 3:
        print("missing mac and human name")
    mac = sys.argv[2]
    name = sys.argv[3]

    with Session(engine) as session:
        session.add(Mac(mac=mac, human_name=name))
        session.commit()


def list_tracked():
    with Session(engine) as session:
        macs = session.exec(select(Mac)).all()
        for mac in macs:
            print(f"mac={mac.mac} name={mac.human_name}")

def watch():
    while True:
        scan()
        time.sleep(5*60)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("missing command, one of: scan, list, history, addmac, tracked")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "scan":
        scan()
    elif cmd == "list":
        list_users()
    elif cmd == "history":
        history()
    elif cmd == "addmac":
        addmac()
    elif cmd == "tracked":
        list_tracked()
    elif cmd == "daemon":
        watch()
