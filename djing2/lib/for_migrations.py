import os


def read_all_file(fname, fl):
    curr_dir = os.path.dirname(os.path.abspath(fl))
    with open(os.path.join(curr_dir, fname), 'r') as f:
        data = f.read(0xffff)
    return data
