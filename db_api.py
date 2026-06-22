import pymysql

def get_conn():
    conn = pymysql.connect(
        host="gateway01.ap-southeast-1.prod.alicloud.tidbcloud.com",
        port=4000,
        user="24z8GsoRjnBAuA2.root",
        password="g6t2cEouIXIg4CXi",
        database="library_db",
        charset="utf8mb4"
    )
    return conn
import streamlit as st
