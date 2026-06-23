import pymysql
import streamlit as st                   
from datetime import datetime, timedelta

def get_db_conn():
    conn = pymysql.connect(
        host=st.secrets["TIDB_HOST"],
        port=int(st.secrets.get("TIDB_PORT", 4000)),
        user=st.secrets["TIDB_USER"],
        password=st.secrets["TIDB_PASSWORD"],
        database=st.secrets["TIDB_DATABASE"],
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        ssl=True  
    )
    return conn

# ========== 图书模块 F01-F04 ==========
def add_book(book_id, title, author, category_id, stock, publisher):
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            sql = """INSERT INTO books(book_id, title, author, category_id, stock, publisher)
                     VALUES (%s, %s, %s, %s, %s, %s)"""
            cur.execute(sql, (book_id, title, author, category_id, stock, publisher))
            conn.commit()
            return True
    except pymysql.IntegrityError:
        conn.rollback()
        return False
    finally:
        conn.close()

def search_book(keyword):
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            sql = """SELECT b.*, c.category_name FROM books b
                     LEFT JOIN category c ON b.category_id = c.category_id
                     WHERE b.title LIKE %s OR b.author LIKE %s"""
            cur.execute(sql, (f"%{keyword}%", f"%{keyword}%"))
            return cur.fetchall()
    finally:
        conn.close()

def update_book(book_id, title, author, category_id, stock, publisher):
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
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
        with conn.cursor() as cur:
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

# ========== 读者模块 F05-F06（补齐缺失的search_reader函数） ==========
def add_reader(reader_id, name, class_name, phone):
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            sql = """INSERT INTO readers(reader_id, name, class_name, phone)
                     VALUES (%s, %s, %s, %s)"""
            cur.execute(sql, (reader_id, name, class_name, phone))
            conn.commit()
            return True
    except pymysql.IntegrityError:
        conn.rollback()
        return False
    finally:
        conn.close()

def search_reader(keyword):
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            sql = """SELECT * FROM readers
                     WHERE reader_id LIKE %s OR name LIKE %s OR class_name LIKE %s"""
            cur.execute(sql, (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"))
            return cur.fetchall()
    finally:
        conn.close()

def delete_reader(reader_id):
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
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

# ========== 借还模块 F07-F08 ==========
def borrow_book(book_id, reader_id):
    conn = get_db_conn()
    try:
        conn.autocommit(False)
        with conn.cursor() as cur:
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
        conn.autocommit(False)
        with conn.cursor() as cur:
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

# ========== 统计模块 F09-F11（补齐缺失get_book_ranking） ==========
def get_borrow_count():
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) total FROM borrow_records WHERE status=0")
            return cur.fetchone()["total"]
    finally:
        conn.close()

def stock_by_category():
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            sql = """SELECT c.category_name, SUM(b.stock) total_stock
                     FROM category c LEFT JOIN books b ON c.category_id = b.category_id
                     GROUP BY c.category_id, c.category_name"""
            cur.execute(sql)
            return cur.fetchall()
    finally:
        conn.close()

def get_book_ranking():
    """F11 图书借阅TOP5排行榜"""
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            sql = """SELECT b.book_id, b.title, COUNT(br.record_id) borrow_times
                     FROM borrow_records br
                     LEFT JOIN books b ON br.book_id = b.book_id
                     GROUP BY br.book_id, b.title
                     ORDER BY borrow_times DESC LIMIT 5"""
            cur.execute(sql)
            return cur.fetchall()
    finally:
        conn.close()

# ==================== 数据库初始化脚本（仅首次运行执行） ====================
def init_database():
    conn = pymysql.connect(
        host="你的TiDB Host地址",
        port=4000,
        user="你的TiDB用户名",
        password="你的TiDB密码",
        charset="utf8mb4"
    )
    cur = conn.cursor()
    cur.execute("CREATE DATABASE IF NOT EXISTS library_system DEFAULT CHARACTER SET utf8mb4;")
    cur.execute("USE library_system;")

    full_sql = """
    SET NAMES utf8mb4;
    SET FOREIGN_KEY_CHECKS = 0;

    DROP TABLE IF EXISTS borrow_records;
    DROP TABLE IF EXISTS books;
    DROP TABLE IF EXISTS readers;
    DROP TABLE IF EXISTS category;

    CREATE TABLE category (
        category_id   VARCHAR(20)  NOT NULL COMMENT '分类编号',
        category_name VARCHAR(50)  NOT NULL COMMENT '分类名称',
        PRIMARY KEY (category_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='图书分类表';

    CREATE TABLE books (
        book_id     VARCHAR(20)  NOT NULL COMMENT '书号',
        title       VARCHAR(100) NOT NULL COMMENT '书名',
        author      VARCHAR(50)  NOT NULL COMMENT '作者',
        category_id VARCHAR(20)  NOT NULL COMMENT '分类编号',
        stock       INT          NOT NULL DEFAULT 0 COMMENT '库存量',
        publisher   VARCHAR(50)  DEFAULT NULL COMMENT '出版社',
        PRIMARY KEY (book_id),
        CONSTRAINT books_ibfk_1 FOREIGN KEY (category_id)
            REFERENCES category (category_id)
            ON UPDATE CASCADE ON DELETE RESTRICT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='图书表';

    CREATE TABLE readers (
        reader_id  VARCHAR(20) NOT NULL COMMENT '学号',
        name       VARCHAR(50) NOT NULL COMMENT '姓名',
        class_name VARCHAR(30) DEFAULT NULL COMMENT '班级',
        phone      VARCHAR(15) DEFAULT NULL COMMENT '手机号',
        PRIMARY KEY (reader_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='读者表';

    CREATE TABLE borrow_records (
        record_id   INT         NOT NULL AUTO_INCREMENT COMMENT '借阅编号',
        book_id     VARCHAR(20) NOT NULL COMMENT '书号',
        reader_id   VARCHAR(20) NOT NULL COMMENT '学号',
        borrow_date DATE        NOT NULL COMMENT '借书日期',
        due_date    DATE        NOT NULL COMMENT '应还日期',
        return_date DATE        DEFAULT NULL COMMENT '实际归还日期',
        status      TINYINT     NOT NULL DEFAULT 0 COMMENT '0未还/1已还',
        PRIMARY KEY (record_id),
        CONSTRAINT borrow_records_ibfk_1 FOREIGN KEY (book_id)
            REFERENCES books (book_id)
            ON UPDATE CASCADE ON DELETE RESTRICT,
        CONSTRAINT fk_br_reader FOREIGN KEY (reader_id)
            REFERENCES readers (reader_id)
            ON UPDATE CASCADE ON DELETE RESTRICT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='借阅记录表';

    INSERT INTO category (category_id, category_name) VALUES
    ('C01', '计算机科学'),('C02', '文学'),('C03', '数学'),('C04', '历史'),
    ('C05', '经济管理'),('C06', '物理'),('C07', '哲学'),('C08', '外语');

    INSERT INTO books (book_id, title, author, category_id, stock, publisher) VALUES
    ('B001', '数据库系统概论', '王珊', 'C01', 5, '高等教育出版社'),
    ('B002', 'Python编程从入门到实践', 'Eric Matthes', 'C01', 3, '人民邮电出版社'),
    ('B003', '红楼梦', '曹雪芹', 'C02', 4, '人民文学出版社'),
    ('B004', '百年孤独', '马尔克斯', 'C02', 2, '南海出版公司'),
    ('B005', '高等数学', '同济大学', 'C03', 6, '高等教育出版社'),
    ('B006', '线性代数', '同济大学', 'C03', 4, '高等教育出版社'),
    ('B007', '中国通史', '吕思勉', 'C04', 3, '华东师范大学出版社'),
    ('B008', '经济学原理', '曼昆', 'C05', 3, '北京大学出版社'),
    ('B009', '数据结构与算法', '严蔚敏', 'C01', 4, '清华大学出版社'),
    ('B010', '活着', '余华', 'C02', 5, '作家出版社'),
    ('B011', '概率论与数理统计', '浙江大学', 'C03', 3, '高等教育出版社'),
    ('B012', '全球通史', '斯塔夫里阿诺斯', 'C04', 2, '北京大学出版社'),
    ('B013', '西方经济学', '高鸿业', 'C05', 4, '中国人民大学出版社'),
    ('B014', '大学物理', '赵凯华', '赵凯华', 'C06', 5, '高等教育出版社'),
    ('B015', '苏菲的世界', '乔斯坦·贾德', 'C07', 3, '作家出版社'),
    ('B016', 'C程序设计语言', '谭浩强', 'C01', 6, '清华大学出版社'),
    ('B017', '围城', '钱钟书', 'C02', 3, '人民文学出版社'),
    ('B018', '新概念英语', 'L G Alexander', 'C08', 4, '外语教学与研究出版社'),
    ('B019', '操作系统概念', 'Silberschatz', 'C01', 3, '机械工业出版社'),
    ('B020', '国富论', '亚当·斯密', 'C05', 2, '商务印书馆');

    INSERT INTO readers (reader_id, name, class_name, phone) VALUES
    ('2024001', '张三', '计科2401', '13800001111'),
    ('2024002', '李四', '计科2401', '13800002222'),
    ('2024003', '王五', '软工2402', '13800003333'),
    ('2024004', '赵六', '数学2401', '13800004444'),
    ('2024005', '孙七', '经济2401', '13800005555'),
    ('2024006', '周八', '计科2402', '13800006666'),
    ('2024007', '吴九', '物理2401', '13800007777'),
    ('2024008', '郑十', '英语2401', '13800008888'),
    ('2024009', '陈晓明', '计科2401', '13800009999'),
    ('2024010', '林小红', '软工2402', '13800010000'),
    ('2024011', '黄大力', '数学2401', '13800011111'),
    ('2024012', '刘芳芳', '经济2401', '13800012222');

    INSERT INTO borrow_records (book_id, reader_id, borrow_date, due_date, return_date, status) VALUES
    ('B001', '2024001', '2026-03-01', '2026-04-01', '2026-03-25', 1),
    ('B003', '2024002', '2026-03-05', '2026-04-05', '2026-03-30', 1),
    ('B005', '2024003', '2026-03-10', '2026-04-10', '2026-04-08', 1),
    ('B002', '2024004', '2026-03-15', '2026-04-15', '2026-04-10', 1),
    ('B010', '2024005', '2026-03-20', '2026-04-20', '2026-04-15', 1),
    ('B001', '2024002', '2026-04-01', '2026-05-01', '2026-04-28', 1),
    ('B009', '2024006', '2026-04-05', '2026-05-05', '2026-05-01', 1),
    ('B016', '2024001', '2026-04-10', '2026-05-10', '2026-05-05', 1),
    ('B004', '2024007', '2026-04-15', '2026-05-15', '2026-05-10', 1),
    ('B013', '2024008', '2026-04-20', '2026-05-20', '2026-05-18', 1),
    ('B001', '2024003', '2026-05-01', '2026-06-01', '2026-05-28', 1),
    ('B003', '2024002', '2026-05-10', '2026-06-10', '2026-06-08', 1),
    ('B005', '2024003', '2026-05-15', '2026-06-15', '2026-06-10', 1),
    ('B011', '2024004', '2026-05-20', '2026-06-20', '2026-06-18', 1),
    ('B001', '2024002', '2026-06-01', '2026-07-01', '2026-06-28', 1),
    ('B008', '2024005', '2026-06-05', '2026-07-05', '2026-07-01', 1),
    ('B016', '2024009', '2026-06-08', '2026-07-08', '2026-07-05', 1),
    ('B019', '2024010', '2026-06-10', '2026-07-10', '2026-07-08', 1),
    ('B020', '2024012', '2026-06-12', '2026-07-12', '2026-07-10', 1),
    ('B002', '2024001', '2026-06-15', '2026-07-15', NULL, 0),
    ('B004', '2024004', '2026-06-18', '2026-07-18', NULL, 0),
    ('B009', '2024006', '2026-06-20', '2026-07-20', NULL, 0),
    ('B015', '2024011', '2026-06-22', '2026-07-22', NULL, 0),
    ('B017', '2024008', '2026-06-25', '2026-07-25', NULL, 0),
    ('B018', '2024010', '2026-06-28', '2026-07-28', NULL, 0);

    SET FOREIGN_KEY_CHECKS = 1;
    """
    sql_segments = full_sql.split(";")
    for seg in sql_segments:
        seg_clean = seg.strip()
        if seg_clean:
            cur.execute(seg_clean)
    conn.commit()
    cur.close()
    conn.close()
    print("TiDB库 library_system 初始化完成！")

# 取消下面注释，运行一次即可初始化数据库
# init_database()
