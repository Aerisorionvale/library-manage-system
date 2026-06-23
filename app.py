import streamlit as st
import pandas as pd
from db_api import get_db_conn

# 页面基础设置
st.set_page_config(page_title="图书管理系统", layout="wide")
st.title("📚 图书管理系统（TiDB云端版）")

# 封装获取连接函数
def get_cursor():
    conn = get_db_conn()
    cur = conn.cursor()
    return conn, cur

# 侧边栏菜单
menu = st.sidebar.selectbox("功能菜单", ["图书管理", "读者管理", "借阅管理", "数据统计"])

# ========== 图书管理模块 ==========
if menu == "图书管理":
    tab_search, tab_add = st.tabs(["图书查询", "新增图书"])

    # 图书查询
    with tab_search:
        st.subheader("图书信息查询")
        keyword = st.text_input("输入图书名称/编号搜索")
        if st.button("查询"):
            conn, cur = get_cursor()
            try:
                sql = """
                SELECT b.book_id 图书编号,b.title 书名,b.author 作者,c.category_name 分类,b.stock 库存,b.publisher 出版社
                FROM books b LEFT JOIN category c ON b.category_id = c.category_id
                WHERE b.book_id LIKE %s OR b.title LIKE %s
                """
                cur.execute(sql, (f"%{keyword}%", f"%{keyword}%"))
                res = cur.fetchall()
                if res:
                    df = pd.DataFrame(res, columns=[desc[0] for desc in cur.description])
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("未查询到匹配图书")
            finally:
                cur.close()
                conn.close()

    # 新增图书（加容错判断，根治KeyError）
    with tab_add:
        st.subheader("添加新图书")
        conn, cur = get_cursor()
        cate_list = []
        try:
            cur.execute("SELECT category_id, category_name FROM category")
            cate_list = cur.fetchall()
        finally:
            cur.close()
            conn.close()

        if not cate_list:
            st.error("数据库暂无分类，请先到TiDB执行分类插入SQL！")
        else:
            cate_dict = {row[1]: row[0] for row in cate_list}
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
                    st.success("✅ 图书新增成功！")
                except Exception as e:
                    conn.rollback()
                    st.error(f"新增失败：{e}")
                finally:
                    cur.close()
                    conn.close()

# ========== 读者管理 ==========
elif menu == "读者管理":
    tab_view, tab_add_reader = st.tabs(["全部读者", "新增读者"])
    with tab_view:
        st.subheader("读者列表")
        conn, cur = get_cursor()
        try:
            cur.execute("SELECT * FROM readers")
            data = cur.fetchall()
            df = pd.DataFrame(data, columns=[d[0] for d in cur.description])
            st.dataframe(df, use_container_width=True)
        finally:
            cur.close()
            conn.close()
    with tab_add_reader:
        st.subheader("新增读者")
        rid = st.text_input("读者编号")
        rname = st.text_input("读者姓名")
        rtype = st.text_input("读者类型/班级")
        phone = st.text_input("联系电话")
        if st.button("添加读者"):
            conn, cur = get_cursor()
            try:
                cur.execute("INSERT INTO readers(reader_id,reader_name,reader_type,phone) VALUES(%s,%s,%s,%s)",
                            (rid, rname, rtype, phone))
                conn.commit()
                st.success("读者添加完成")
            except Exception as e:
                conn.rollback()
                st.error(f"失败：{e}")
            finally:
                cur.close()
                conn.close()

# ========== 借阅管理 ==========
elif menu == "借阅管理":
    tab_record, tab_borrow = st.tabs(["借阅记录", "办理借书"])
    with tab_record:
        st.subheader("全部借阅记录")
        conn, cur = get_cursor()
        try:
            sql = """
            SELECT br.record_id, r.reader_name, b.title, br.borrow_date, br.due_date, br.return_date, br.status
            FROM borrow_records br
            LEFT JOIN readers r ON br.reader_id=r.reader_id
            LEFT JOIN books b ON br.book_id=b.book_id
            """
            cur.execute(sql)
            res = cur.fetchall()
            df = pd.DataFrame(res, columns=[d[0] for d in cur.description])
            st.dataframe(df, use_container_width=True)
        finally:
            cur.close()
            conn.close()
    with tab_borrow:
        st.subheader("借书操作")
        conn, cur = get_cursor()
        r_list = []
        b_list = []
        try:
            cur.execute("SELECT reader_id,reader_name FROM readers")
            r_list = cur.fetchall()
            cur.execute("SELECT book_id,title FROM books WHERE stock>0")
            b_list = cur.fetchall()
        finally:
            cur.close()
            conn.close()
        if r_list and b_list:
            r_dict = {i[1]:i[0] for i in r_list}
            b_dict = {i[1]:i[0] for i in b_list}
            sel_r = st.selectbox("选择读者", list(r_dict.keys()))
            sel_b = st.selectbox("选择图书", list(b_dict.keys()))
            days = st.number_input("借阅天数", min_value=7, value=30)
            if st.button("确认借书"):
                from datetime import date, timedelta
                today = date.today()
                due = today + timedelta(days=days)
                conn, cur = get_cursor()
                try:
                    cur.execute("""
                    INSERT INTO borrow_records(reader_id,book_id,borrow_date,due_date,status)
                    VALUES(%s,%s,%s,%s,0)
                    """, (r_dict[sel_r], b_dict[sel_b], today, due))
                    cur.execute("UPDATE books SET stock=stock-1 WHERE book_id=%s", (b_dict[sel_b],))
                    conn.commit()
                    st.success("借书成功！")
                except Exception as e:
                    conn.rollback()
                    st.error(f"失败：{e}")
                finally:
                    cur.close()
                    conn.close()
        else:
            st.warning("请先录入读者和可借阅图书")

# ========== 数据统计 ==========
elif menu == "数据统计":
    st.subheader("系统数据统计")
    conn, cur = get_cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM books")
        book_num = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM readers")
        reader_num = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM borrow_records WHERE status=0")
        borrow_num = cur.fetchone()[0]
        col1,col2,col3 = st.columns(3)
        with col1:
            st.metric("图书总数", book_num)
        with col2:
            st.metric("读者总数", reader_num)
        with col3:
            st.metric("在借图书", borrow_num)
    finally:
        cur.close()
        conn.close()
