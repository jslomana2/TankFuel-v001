#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os, sys
from flask import Flask, jsonify
from dbfread import DBF

app = Flask(__name__)

def read_dbf(file_path, encoding="latin-1", lower_names=True, limit=None):
    table = DBF(file_path, load=True, encoding=encoding,
                lowernames=lower_names, ignore_missing_memofile=True)
    rows = [dict(r) for r in table]
    if limit is not None:
        rows = rows[:int(limit)]
    return rows

@app.route("/api/test")
def api_test():
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(port=5000, debug=True)
