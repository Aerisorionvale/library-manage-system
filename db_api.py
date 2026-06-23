import mysql.connector
from mysql.connector import Error as MySQLError
import streamlit as st
from datetime import datetime, timedelta


def get_db_conn():
    """
    获取 TiDB Cloud 数据库连接对象
    使用 mysql.connector 驱动
    """
    # 先读取所有连接信息，打印出来方便调试
    try:
        conn = mysql.connector.connect(
            host=st.secrets["TIDB_HOST"],
            port=int(st.secrets.get("TIDB_PORT", 4000)),
            user=st.secrets["TIDB_USER"],
            password=st.secrets["TIDB_PASSWORD"],
            database=st.secrets["TIDB_DATABASE"],
            charset="utf8mb4",
            connection_timeout=10,
            autocommit=False
        )
        return conn
    except MySQLError as e:
        # 在页面上显示真实的错误信息，不再被 redacted
        st.error(f"数据库连接失败！错误代码: {e.errno}, 错误信息: {e.msg}")
        st.error(f"完整错误: {str(e)}")
        st.error(f"SQLSTATE: {e.sqlstate}")
        raise


# ========== 图书操作 ==========
def add_book(book_id, title, author, category_id, stock, publisher):
    conn = get_db_conn()
    try:
        cur = conn.cursor(dictionary=True)
        sql = """INSERT INTO books(book_id, title, author, category_id, stock, publisher)
                 VALUES (%s, %s, %s, %s, %s, %s)"""
        cur.execute(sql, (book_id, title, author, category_id, stock, publisher))
        conn.commit()
        return True
    except mysql.connector.IntegrityError:
        conn.rollback()
        return False
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()


def search_book(keyword):
    conn = get_db_conn()
    try:
        cur = conn.cursor(dictionary=True)
        sql = """SELECT b.*, c.category_name FROM books b
                 LEFT JOIN category c ON b.category_id = c.category_id
                 WHERE b.title LIKE %s OR b.author LIKE %s"""
        cur.execute(sql, (f"%{keyword}%", f"%{keyword}%"))
        result = cur.fetchall()
        return result
    finally:
        conn.close()


def update_book(book_id, title, author, category_id, stock, publisher):
    conn = get_db_conn()
    try:
        cur = conn.cursor(dictionary=True)
        sql = """UPDATE books SET title=%s, author=%s, category_id=%s, stock=%s, publisher=%s
                 WHERE book_id=%s"""
        cur.execute(sql, (title, author, category_id, stock, publisher, book_id))
        conn.commit()
        return cur.rowcount > 0
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()


def delete_book(book_id):
    conn = get_db_conn()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT COUNT(*) cnt FROM borrow_records WHERE book_id=%s AND status=0", (book_id,))
        if cur.fetchone()["cnt"] > 0:
            return False
        cur.execute("DELETE FROM books WHERE book_id=%s", (book_id,))
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()


# ========== 读者操作 ==========
def add_reader(reader_id, name, class_name, phone):
    conn = get_db_conn()
    try:
        cur = conn.cursor(dictionary=True)
        sql = """INSERT INTO readers(reader_id, name, class_name, phone)
                 VALUES (%s, %s, %s, %s)"""
        cur.execute(sql, (reader_id, name, class_name, phone))
        conn.commit()
        return True
    except mysql.connector.IntegrityError:
        conn.rollback()
        return False
    finally:
        conn.close()


def search_reader(keyword):
    conn = get_db_conn()
    try:
        cur = conn.cursor(dictionary=True)
        sql = """SELECT * FROM readers
                 WHERE reader_id LIKE %s OR name LIKE %s OR class_name LIKE %s"""
        cur.execute(sql, (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"))
        return cur.fetchall()
    finally:
        conn.close()


def delete_reader(reader_id):
    conn = get_db_conn()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT COUNT(*) cnt FROM borrow_records WHERE reader_id=%s AND status=0", (reader_id,))
        if cur.fetchone()["cnt"] > 0:
            return False
        cur.execute("DELETE FROM readers WHERE reader_id=%s", (reader_id,))
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()


# ========== 借还书 ==========
def borrow_book(book_id, reader_id):
    conn = get_db_conn()
    try:
        conn.autocommit = False
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT stock FROM books WHERE book_id=%s", (book_id,))
        book = cur.fetchone()
        if not book or book["stock"] <= 0:
            return False, "库存不足，无法借阅"
        borrow_date = datetime.now().date()
        due_date = borrow_date + timedelta(days=30)
        cur.execute("""INSERT INTO borrow_records(book_id, reader_id, borrow_date, due_date, status)
                       VALUES (%s, %s, %s, %s, 0)""", (book_id, reader_id, borrow_date, due_date))
        cur.execute("UPDATE books SET stock = stock - 1 WHERE book_id=%s", (book_id,))
        conn.commit()
        return True, f"借阅成功，应于{due_date}前归还"
    except Exception as e:
        conn.rollback()
        return False, f"借阅失败：{str(e)}"
    finally:
        conn.close()


def return_book(record_id):
    conn = get_db_conn()
    try:
        conn.autocommit = False
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT book_id, status FROM borrow_records WHERE record_id=%s", (record_id,))
        record = cur.fetchone()
        if not record:
            return False, "无此借阅记录"
        if record["status"] == 1:
            return False, "该书已归还，无需重复操作"
        cur.execute("""UPDATE borrow_records SET return_date=%s, status=1 WHERE record_id=%s""",
                    (datetime.now().date(), record_id))
        cur.execute("UPDATE books SET stock = stock + 1 WHERE book_id=%s", (record["book_id"],))
        conn.commit()
        return True, "还书成功，库存已更新"
    except Exception as e:
        conn.rollback()
        return False, f"还书失败：{str(e)}"
    finally:
        conn.close()


# ========== 统计函数 ==========
def get_borrow_count():
    conn = get_db_conn()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT COUNT(*) total FROM borrow_records WHERE status=0")
        return cur.fetchone()["total"]
    finally:
        conn.close()


def stock_by_category():
    conn = get_db_conn()
    try:
        cur = conn.cursor(dictionary=True)
        sql = """SELECT c.category_name, SUM(b.stock) total_stock
                 FROM category c LEFT JOIN books b ON c.category_id = b.category_id
                 GROUP BY c.category_id, c.category_name"""
        cur.execute(sql)
        return cur.fetchall()
    finally:
        conn.close()


def get_book_ranking():
    conn = get_db_conn()
    try:
        cur = conn.cursor(dictionary=True)
        sql = """SELECT b.book_id, b.title, COUNT(br.record_id) borrow_times
                 FROM borrow_records br
                 LEFT JOIN books b ON br.book_id = b.book_id
                 GROUP BY br.book_id, b.title
                 ORDER BY borrow_times DESC LIMIT 5"""
        cur.execute(sql)
        return cur.fetchall()
    finally:
        conn.close()
