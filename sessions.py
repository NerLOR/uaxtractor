#!/bin/env python3

import argparse
import os
import phpserialize


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('sess_dir', type=str)
    args = parser.parse_args()
    for filename in os.listdir(args.sess_dir):
        if not filename.startswith('sess_'):
            continue
        with open(f'{args.sess_dir}/{filename}', 'rb') as f:
            session = phpserialize.loads(f.read(), decode_strings=True)
            print(session)
