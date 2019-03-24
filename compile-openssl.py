import os
import sys
sys.path.append(os.path.abspath('../utils'))

import magic
import db_operation
import udload
import subprocess
import hashlib
import shutil

repo_imagemagick = 1903522
working_dir = os.getcwd()

def hashfile(f, blocksize=65536):
    """
    Compute hash value of the specified file
        ...here is sha256...
    Parameters:
        f, file path, type of string
    Return:
        hash value if success otherwise None
    """
    try:

        if not os.path.exists(f):
            return None

        afile = open(f, "rb")
        hasher = hashlib.sha256()
        buf = afile.read(blocksize)
        while len(buf) > 0:
            hasher.update(buf)
            buf = afile.read(blocksize)

        afile.close()
        return hasher.hexdigest()

    except Exception as e:
        print e
        afile.close()
        return None


def upload(fpath, fname, tag):
    try:
        #get the file's hashcode
        hashvalue = hashfile(fpath)
        if hashvalue is None:
            return False
        if udload.upload_to_ceph(fpath, hashvalue) == False:
            return False
        if db_operation.add_openssl_bin(hashvalue, fname, tag) < 0:
            return False
        return True
    except Exception, e:
        print e
        return False


if __name__ == "__main__":
    start = int(sys.argv[1])
    limit = int(sys.argv[2])
    repo = 7634677 
    commit_list = db_operation.get_commit_version_snapshots(repo, start, limit)
    print commit_list, len(commit_list)
    #exit(0)
    #print working_dir
    processed = db_operation.get_processed_commit_version_snapshots_openssl()
    print processed
    #exit(0)

    print 'workingdir:'+working_dir
    for (name, uri) in commit_list:
        print '\t\t', name+' uri : '+uri
        if name in processed:
            print '[processed]'
            continue
        #path = os.path.join(working_dir, uri)
        #print path
        
        if not udload.download_from_commonstorage(uri, uri):
            print 'download failed'
            continue

        unzip_cmd = 'unzip ' + uri + ' -d openssl-' +name
        print unzip_cmd
        process = subprocess.Popen(unzip_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        our, err = process.communicate()
        errcode = process.returncode
        if errcode < 0:
            print '[ERROE]', errcode, err
            continue
        print 'download success!'
        path = os.path.join(working_dir,'openssl-' +name)
        print path
        #exit(0)

        for f in os.listdir(path):
            path = os.path.join(path, f)
            break
        print path

        compile_cmd = 'cd ' + path + ' && ' \
                     + './config && ' \
                     + 'make &&' \
                     + ' cd ' + working_dir
        print compile_cmd
        #exit(-1)
        process = subprocess.Popen(compile_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        out, err = process.communicate()
        errcode = process.returncode
        if errcode < 0:
            print '[ERROR]', errcode, err
            continue
        
        #path = os.path.join(path, 'build-gcc')
        #print path
        #exit(-1)

        for root, _, files in os.walk(path):
            for fname in files:
                fpath = os.path.join(root, fname)
                m = magic.from_file(fpath).lower()
                #print fpath, m
                if 'elf ' not in m:
                    continue
                print fpath , fpath.split(path)[1]
                upload(fpath, fpath.split(path)[1], name)
        
        os.remove(os.path.join(working_dir, uri))
        shutil.rmtree(os.path.join(working_dir, 'openssl-'+name))
        #break
