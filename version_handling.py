import subprocess

def get_version():
    tags = subprocess.check_output(["git", "tag", "-l",
        "v*.*.*", "--sort", "v:refname"]).split("\n")
    for tag in reversed(tags):
        if tag:
           ver = tag[1:].split(".")
           major = int(ver[0])
           minor = int(ver[1])
           build = int(ver[2])
           break
    else:
        major = 0
        minor = 0
        build = 0
    return major, minor, build
