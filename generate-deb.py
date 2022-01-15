#!/usr/bin/env python3


from os import path
from pathlib import Path
import xml.etree.ElementTree as ET

import yaml
from requests import get


rosdeps = None
rosdeps_python = None
packages = {}
dependencies = set()
deb_dependencies = []


def get_packages_xmls(path: str):
    return Path(path).rglob("**/package.xml")


def parse_packages_xmls(path: str):
    for xml in get_packages_xmls(path):
        tree = ET.parse(xml)
        name = tree.find("name").text
        run_depend = [e.text for e in tree.findall("run_depend")]
        depend = [e.text for e in tree.findall("depend")]
        exec_depend = [e.text for e in tree.findall("exec_depend")]
        packages.update({name: run_depend + depend + exec_depend})


def fetch_rosdeps():
    """Fetch rosdeps from Github"""
    global rosdeps, rosdeps_python
    base = "https://raw.githubusercontent.com/ros/rosdistro/master/rosdep/base.yaml"
    python = "https://raw.githubusercontent.com/ros/rosdistro/master/rosdep/python.yaml"
    rosdeps = yaml.safe_load(get(base).text)
    rosdeps_python = yaml.safe_load(get(python).text)


def resolve_dependencies(path):
    parse_packages_xmls(path)
    for p in packages:
        for dep in packages[p]:
            if dep not in packages:
                dependencies.add(dep)


def getBusterPackageName(debian):
    if "buster" in debian and debian["buster"] is not None:
        return debian["buster"]
    elif "*" in debian:
        return debian["*"]
    else:
        return debian


def dependencies_for_debian(path):
    global deb_dependencies
    fetch_rosdeps()
    resolve_dependencies(path)
    for dep in dependencies:
        try:
            deb_dependencies += getBusterPackageName(rosdeps[dep]["debian"])
        except KeyError:
            if dep in rosdeps_python:
                deb_dependencies += getBusterPackageName(rosdeps_python[dep]["debian"])
            else:
                print(f"No package for {dep} could be found for Debian (10) Buster")
    deb_dependencies.sort()


def generate_nfpm_config():
    with open("templates/ros2-base-packages.yaml", "r") as f:
        config = yaml.safe_load(f.read())
    config["depends"] = deb_dependencies
    with open("ros2-base-packages.yaml", "w") as f:
        f.write(yaml.dump(config))


if __name__ == "__main__":
    dependencies_for_debian("./install_aarch64")
    generate_nfpm_config()
