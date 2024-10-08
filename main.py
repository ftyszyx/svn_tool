import os
import sys
import subprocess
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET


def _decode_bytes(byte_text: bytes):
    try:
        res_text = byte_text.decode("utf-8")
    except UnicodeDecodeError:
        res_text = byte_text.decode("gbk")
    return res_text


def run_command(cmd):
    print(f"\nrun cmd: {cmd}\n")
    try:
        result = subprocess.run(cmd, capture_output=True, shell=True)
        if result.returncode != 0:
            print(f"cmd: {cmd} \nError: {result.stderr}")
            sys.exit(1)
        return _decode_bytes(result.stdout)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def get_revision_from_date(svn_path, target_date: datetime):
    formatted_date = target_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    cmd = f'svn log -r "{{{formatted_date}}}:1" --limit 1 {svn_path} --xml'
    result = run_command(cmd)
    root = ET.fromstring(result)
    revision = root.find("logentry").attrib["revision"]
    print("get revision", svn_path, target_date, revision)
    return revision


def get_date_from_revision(svn_path, revision) -> datetime:
    cmd = f"svn log -r {revision} --limit 1 {svn_path} --xml"
    result = run_command(cmd)
    date = result.split("</date>")[0].split("<date>")[1].strip()
    print("get date", date)
    return datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.%fZ")


def get_externals(svn_path, target_ver):
    cmd = f"svn propget svn:externals  -R {svn_path} --xml"
    result = run_command(cmd)
    root = ET.fromstring(result)
    externals = []
    for target in root.findall(".//target"):
        property_tag = target.find("property")
        target_path = target.attrib["path"]
        if property_tag is not None and property_tag.get("name") == "svn:externals":
            lines = property_tag.text.strip().split("\n")
            for line in lines:
                parts = line.split(" ")
                if len(parts) >= 2:
                    externals.append(os.path.join(target_path, parts[-1]))
    return externals


def revert_svn_to_id(svn_path, target_id):
    reversion_date = get_date_from_revision(svn_path, target_id)
    print(f"Reverting to revision {target_id} ({reversion_date})")
    cmd = f"svn update -r {target_id} {svn_path}"
    result = run_command(cmd)
    print(f"update to {target_id} completed")
    externals = get_externals(svn_path, target_id)
    for external_path in externals:
        print(f"Reverting external directory: {external_path}")
        versionid = get_revision_from_date(external_path, reversion_date)
        cmd = f"svn update -r {versionid} {external_path}"
        result = run_command(cmd)

    print("Reversion completed successfully.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python main.py <svn_path> <target_id>")
        print("Example: python main.py /path/to/svn/repo 530618")
        sys.exit(1)

    svn_path = sys.argv[1]
    target_id = sys.argv[2]

    try:
        revert_svn_to_id(svn_path, target_id)
    except Exception as e:
        print(f"Error: {e}")
