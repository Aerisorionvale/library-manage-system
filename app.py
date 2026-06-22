import streamlit as st
import pandas as pd
from db_api import get_db_conn

# 页面基础配置
st.set_page_config(page_title="图书管理系统", layout="wide")
st.title("📚 图书管理系统（TiDB云端版）")

# 封装独立获取游标函数，避免全局共用连接导致错乱
def get_cursor():
    conn = get_db_conn()
    cur = conn.cursor()
    return conn, cur

# 侧边栏功能导航
menu = st.sidebar.selectbox("功能菜单", ["图书查询", "新增图书", "读者管理", "借阅管理", "数据统计"])

# 1.图书查询模块（修复SQL注入漏洞，改用参数化查询）
if menu == "图书查询":
    st.subheader("图书信息查询")
    search_key = st.text_input("输入图书名称/编号搜索")
    if st.button("查询"):
        conn, cur = get_cursor()
        try:
            if search_key:
                sql = """
                SELECT b.book_id 图书编号,b.title 书名,b.author 作者,c.category_name 分类,
                       b.stock 库存,b.publisher 出版社
                FROM books b LEFT JOIN category c ON b.category_id = c.category_id
                WHERE b.book_id LIKE %s OR b.title LIKE %s
                """
                params = (f"%{search_key}%", f"%{search_key}%")
            else:
                sql = """
                SELECT b.book_id 图书编号,b.title 书名,b.author 作者,c.category_name 分类,
                       b.stock 库存,b.publisher 出版社
                FROM books b LEFT JOIN category c ON b.category_id = c.category_id
                """
                params = ()
            cur.execute(sql, params)
            res = cur.fetchall()
            col = [i[0] for i in cur.description]
            df = pd.DataFrame(res, columns=col)
            st.dataframe(df, use_container_width=True)
        finally:
            cur.close()
            conn.close()

# 2.新增图书模块
elif menu == "新增图书":
    st.subheader("添加新图书")
    conn, cur = get_cursor()
    try:
        c_sql = "SELECT category_id,category_name FROM category"
        cur.execute(c_sql)
        cate_list = cur.fetchall()
        cate_dict = {i[1]: i[0] for i in cate_list}
    finally:
        cur.close()
        conn.close()

    cate_name = st.selectbox("图书分类", list(cate_dict.keys()))
    book_id = st.text_input("图书编号")
    title = st.text_input("图书名称")
    author = st.text_input("作者")
    stock = st.number_input("库存数量", min_value=1, value=1)
    pub = st.text_input("出版社")
    if st.button("提交新增"):
        conn, cur = get_cursor()
        try:
            cid = cate_dict[cate_name]
            insert_sql = """
            INSERT INTO books(book_id,title,author,category_id,stock,publisher)
            VALUES(%s,%s,%s,%s,%s,%s)
            """
            cur.execute(insert_sql, (book_id, title, author, cid, stock, pub))
            conn.commit()
            st.success("图书新增成功！")
        except Exception as e:
            conn.rollback()
            st.error(f"新增失败：{e}")
        finally:
            cur.close()
            conn.close()

# 3.读者管理模块（修复致命字段不匹配问题，对齐你数据表 readers 结构）
elif menu == "读者管理":
    tab1, tab2 = st.tabs(["读者列表", "新增读者"])
    with tab1:
        conn, cur = get_cursor()
        try:
            cur.execute("SELECT * FROM readers")
            reader_data = cur.fetchall()
            reader_col = [i[0] for i in cur.description]
            st.dataframe(pd.DataFrame(reader_data, columns=reader_col), use_container_width=True)
        finally:
            cur.close()
            conn.close()
    with tab2:
        rid = st.text_input("读者编号")
        rname = st.text_input("读者姓名")
        rclass = st.text_input("班级")
        phone = st.text_input("联系电话")
        if st.button("添加读者"):
            conn, cur = get_cursor()
            try:
                # 字段修正：reader_name → name，reader_type → class_name
                ins_sql = "INSERT INTO readers(reader_id,name,class_name,phone) VALUES(%s,%s,%s,%s)"
                cur.execute(ins_sql, (rid, rname, rclass, phone))
                conn.commit()
                st.success("读者添加完成")
            except Exception as e:
                conn.rollback()
                st.error(f"失败：{e}")
            finally:
                cur.close()
                conn.close()

# 4.借阅管理模块
elif menu == "借阅管理":
    tab1, tab2 = st.tabs(["借阅记录", "图书借阅"])
    with tab1:
        conn, cur = get_cursor()
        try:
            borrow_sql = """
            SELECT br.record_id, r.name 读者, b.title 图书, br.borrow_date 借出日期,
                   br.due_date 应还日期, br.return_date 归还日期, br.status
            FROM borrow_records br
            LEFT JOIN readers r ON br.reader_id = r.reader_id
            LEFT JOIN books b ON br.book_id = b.book_id
            """
            cur.execute(borrow_sql)
            borrow_data = cur.fetchall()
            borrow_col = [i[0] for i in cur.description]
            st.dataframe(pd.DataFrame(borrow_data, columns=borrow_col), use_container_width=True)
        finally:
            cur.close()
            conn.close()

    with tab2:
        conn, cur = get_cursor()
        try:
            cur.execute("SELECT reader_id,name FROM readers")
            r_all = cur.fetchall()
            r_select = {f"{i[0]} {i[1]}": i[0] for i in r_all}
            cur.execute("SELECT book_id,title FROM books WHERE stock>0")
            b_all = cur.fetchall()
            b_select = {f"{i[0]} {i[1]}": i[0] for i in b_all}
        finally:
            cur.close()
            conn.close()

        sel_r = st.selectbox("选择读者", list(r_select.keys()))
        sel_b = st.selectbox("选择借阅图书", list(b_select.keys()))
        due_day = st.number_input("借阅天数", min_value=7, value=30)
        if st.button("确认借阅"):
            rid = r_select[sel_r]
            bid = b_select[sel_b]
            conn, cur = get_cursor()
            try:
                borrow_sql = """
                INSERT INTO borrow_records(reader_id,book_id,borrow_date,due_date,status)
                VALUES(%s,%s,CURRENT_DATE(),DATE_ADD(CURRENT_DATE(),INTERVAL %s DAY),0)
                """
                stock_sql = "UPDATE books SET stock=stock-1 WHERE book_id=%s"
                cur.execute(borrow_sql, (rid, bid, due_day))
                cur.execute(stock_sql, (bid,))
                conn.commit()
                st.success("借阅登记成功！")
            except Exception as e:
                conn.rollback()
                st.error(f"操作失败：{e}")
            finally:
                cur.close()
                conn.close()

# 5.数据统计模块（增加空值判断，避免索引报错）
elif menu == "数据统计":
    st.subheader("系统数据统计")
    conn, cur = get_cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM books")
        book_total = cur.fetchone()[0] if cur.fetchone() else 0
        cur.execute("SELECT COUNT(*) FROM readers")
        reader_total = cur.fetchone()[0] if cur.fetchone() else 0
        cur.execute("SELECT COUNT(*) FROM borrow_records WHERE status=0")
        borrow_out = cur.fetchone()[0] if cur.fetchone() else 0
    finally:
        cur.close()
        conn.close()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("图书总数量", book_total)
    with col2:
        st.metric("读者总数", reader_total)
    with col3:
        st.metric("当前借出图书", borrow_out)
