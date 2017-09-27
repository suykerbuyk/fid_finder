#!/usr/bin/env python
# vim: autoindent tabstop=4 shiftwidth=4 expandtab softtabstop=4 filetype=python

import os,subprocess, sys, binascii

shell_cmd="lfs"
shell_cmd_params="hsm_state"
delim=': (0x'
delim_len=len(delim)-3

def asciisafewalk(top, topdown=True, onerror=None, followlinks=False):
    """
    duplicate of os.walk, except we do a forced decode after listdir
    """
    islink, join, isdir = os.path.islink, os.path.join, os.path.isdir

    try:
        # Note that listdir and error are globals in this module due
        # to earlier import-*.
        names = os.listdir(top)
        # force non-ascii text out
        names = [name.decode('utf8','ignore') for name in names]
    except os.error, err:
        if onerror is not None:
            onerror(err)
        return

    dirs, nondirs = [], []
    for name in names:
        if isdir(join(top, name)):
            dirs.append(name)
        else:
            nondirs.append(name)

    if topdown:
        yield top, dirs, nondirs
    for name in dirs:
        new_path = join(top, name)
        if followlinks or not islink(new_path):
            for x in asciisafewalk(new_path, topdown, onerror, followlinks):
                yield x
    if not topdown:
        yield top, dirs, nondirs


try:
    shell_cmd=subprocess.check_output\
            (["which", shell_cmd], stderr=subprocess.STDOUT).strip()
    shell_cmd=shell_cmd.decode()
except subprocess.CalledProcessError as e:
    msg=e.output.decode()
    print("Missing shell command: ", shell_cmd)
    print("Error Msg: " + msg)
    sys.exit(1)

def finder(start_path):
    for root, dirnames, filenames in asciisafewalk(os.path.abspath(start_path)):
        for name in filenames:
            file= os.path.join(root,name)
            try:
                archived=False
                released=False
                cmd_out=subprocess.check_output\
                    ([shell_cmd, shell_cmd_params, file],\
                    stderr=subprocess.STDOUT).strip()
                result=cmd_out.decode('utf-8','ignore')
                idx=result.find(delim)
                if idx > 1 :
                    fname=result[:idx]
                    fstate=result[idx+delim_len:]
                    archived=fstate.find("archived") > 0
                    released=fstate.find("released") > 0
                if archived:
                    fid_attr=subprocess.check_output\
                        (['getfattr',  '--absolute-names', '-e', 'hex', '-n', 'user.mlhsm_archive_fid', file])
                    fid_line=fid_attr.splitlines()[1]
                    fid_line=fid_line[fid_line.find('=')+3:]
                    fid_line=fid_line[:32]
                    fid_top=fid_line[:16].lstrip('0')
                    fid_bot=fid_line[16:].lstrip('0')
                    mfid=fid_top + ":" + fid_bot
                    out=mfid
                    if released:
                        out += "\treleased"
                    else:
                        out += "\tarchived"
                    out += "\t" + fname
                    try:
                        print(out.decode('utf-8','ignore'))
                    except:
                        altout = [elem.encode('hex') for elem in out]
                        print("Problem string: ", altout)

            except subprocess.CalledProcessError as e:
                # altout = [elem.encode('hex') for elem in out]
                print("0000000:00000\t FAILURE\t " + shell_cmd + shell_cmd_params + file)
                # print(altout)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Requires path to top lustre directory to search for archive fids")
        sys.exit(1)
    start_path=unicode(sys.argv[1])
    if False == os.path.isdir(start_path):
        print("Not a valid directory: " + start_path)
        sys.exit(1)
    finder(start_path)

