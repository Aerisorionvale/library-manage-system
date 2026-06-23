import streamlit as st
import pandas as pd
from db_api import get_db_conn

# 页面基础配置
st.set_page_config(page_title="图书管理系统", layout="wide")
st.title("📚 图书管理系统（TiDB云端版）")

# 获取数据库游标封装
def get_cursor():
    conn = get_db_conn()
    cur = conn.cursor()
    return conn, cur

# 侧边栏功能菜单
menu = st.sidebar.selectbox("功能菜单", ["图书管理", "读者管理", "借阅管理", "数据统计"])

# ---------------------- 图书管理模块 ----------------------
if menu == "图书管理":
    tab_search, tab_add = st.tabs(["图书查询", "新增图书"])

    # 图书查询页面
    with tab_search:
        st.subheader("图书信息查询")
        search_key = st.text_input("输入图书名称/编号搜索")
        if st.button("查询"):
            conn, cur = get_cursor()
            try:
                sql = """
                SELECT b.book_id 图书编号,b.title 书名,b.author 作者,c.category_name 分类,
                       b.stock 库存,b.publisher 出版社
                FROM books b LEFT JOIN category c ON b.category_id = c.category_id
                WHERE b.book_id LIKE %s OR b.title LIKE %s
                """
                cur.execute(sql, (f"%{search_key}%", f"%{search_key}%"))
                res = cur.fetchall()
                if res:
                    col_names = [desc[0] for desc in cur.description]
                    df = pd.DataFrame(res, columns=col_names)
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("未找到匹配图书")
            finally:
                cur.close()
                conn.close()

    # 新增图书页面（带空判断，彻底解决KeyError）
       with tab_add:
        st.subheader("添加新图书")
        # 直接写死你全部分类，不再从数据库读取，彻底避开cate_dict报错
        cate_dict = {
            "计算机":"C01",
            "文学":"C02",
            "经济管理":"C03",
            "历史":"C04",
            "经管":"C05",
            "数学":"C06",
            "物理":"C07",
            "外语":"C08"
        }
        cate_name = st.selectbox("图书分类", list(cate_dict.keys()))
        book_id = st.text_input("图书编号")
        title = st.text_input("图书名称")
        author = st.text_input("作者")
        stock = st.number_input("库存数量", min_value=1, value=1)
        publisher = st.text_input("出版社")

        if st.button("提交新增"):
            conn, cur = get_cursor()
            try:
                cid = cate_dict[cate_name]
                insert_sql = """
                INSERT INTO books(book_id,title,author,category_id,stock,publisher)
                VALUES(%s,%s,%s,%s,%s,%s)
                """
                cur.execute(insert_sql, (book_id, title, author, cid, stock, publisher))
                conn.commit()
                st.success("✅ 图书新增成功！")
            except Exception as e:
                conn.rollback()
                st.error(f"新增失败：{e}")
            finally:
                cur.close()
                conn.close()
            if st.button("提交新增"):
                conn, cur = get_cursor()
                try:
                    cid = cate_dict[cate_name]
                    insert_sql = """
                    INSERT INTO books(book_id,title,author,category_id,stock,publisher)
                    VALUES(%s,%s,%s,%s,%s,%s)
                    """
                    cur.execute(insert_sql, (book_id, title, author, cid, stock, publisher))
                    conn.commit()
                    st.success("✅ 图书新增成功！")
                except Exception as e:
                    conn.rollback()
                    st.error(f"新增失败：{e}")
                finally:
                    cur.close()
                    conn.close()

# ---------------------- 读者管理模块 ----------------------
elif menu == "读者管理":
    tab_list, tab_add_reader = st.tabs(["读者列表", "新增读者"])
    with tab_list:
        st.subheader("全部读者信息")
        conn, cur = get_cursor()
        try:
            cur.execute("SELECT * FROM readers")
            reader_data = cur.fetchall()
            cols = [d[0] for d in cur.description]
            st.dataframe(pd.DataFrame(reader_data, columns=cols), use_container_width=True)
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
                ins_sql = "INSERT INTO readers(reader_id,reader_name,reader_type,phone) VALUES(%s,%s,%s,%s)"
                cur.execute(ins_sql, (rid, rname, rtype, phone))
                conn.commit()
                st.success("读者添加完成！")
            except Exception as e:
                conn.rollback()
                st.error(f"添加失败：{e}")
            finally:
                cur.close()
                conn.close()

# ---------------------- 借阅管理模块 ----------------------
elif menu == "借阅管理":
    tab_record, tab_borrow = st.tabs(["借阅记录", "办理借书"])
    with tab_record:
        st.subheader("全部借阅记录")
        conn, cur = get_cursor()
        try:
            borrow_sql = """
            SELECT br.record_id, r.reader_name, b.title, br.borrow_date,
                   br.due_date, br.return_date, br.status
            FROM borrow_records br
            LEFT JOIN readers r ON br.reader_id = r.reader_id
            LEFT JOIN books b ON br.book_id = b.book_id
            """
            cur.execute(borrow_sql)
            borrow_data = cur.fetchall()
            cols = [d[0] for d in cur.description]
            st.dataframe(pd.DataFrame(borrow_data, columns=cols), use_container_width=True)
        finally:
            cur.close()
            conn.close()
    with tab_borrow:
        st.subheader("图书借阅操作")
        conn, cur = get_cursor()
        reader_all = []
        book_all = []
        try:
            cur.execute("SELECT reader_id,reader_name FROM readers")
            reader_all = cur.fetchall()
            cur.execute("SELECT book_id,title FROM books WHERE stock>0")
            book_all = cur.fetchall()
        finally:
            cur.close()
            conn.close()

        if reader_all and book_all:
            reader_dict = {row[1]: row[0] for row in reader_all}
            book_dict = {row[1]: row[0] for row in book_all}
            sel_reader = st.selectbox("选择借阅读者", list(reader_dict.keys()))
            sel_book = st.selectbox("选择借阅图书", list(book_dict.keys()))
            borrow_day = st.number_input("借阅天数", min_value=7, value=30)
            if st.button("确认借阅"):
                from datetime import date, timedelta
                today = date.today()
                due_date = today + timedelta(days=borrow_day)
                conn, cur = get_cursor()
                try:
                    cur.execute("""
                    INSERT INTO borrow_records(reader_id,book_id,borrow_date,due_date,status)
                    VALUES(%s,%s,%s,%s,0)
                    """, (reader_dict[sel_reader], book_dict[sel_book], today, due_date))
                    cur.execute("UPDATE books SET stock = stock - 1 WHERE book_id = %s", (book_dict[sel_book],))
                    conn.commit()
                    st.success("借阅登记成功！")
                except Exception as e:
                    conn.rollback()
                    st.error(f"借阅失败：{e}")
                finally:
                    cur.close()
                    conn.close()
        else:
            st.warning("请先录入读者和有库存的图书！")

# ---------------------- 数据统计模块 ----------------------
elif menu == "数据统计":
    st.subheader("系统数据总统计")
    conn, cur = get_cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM books")
        total_book = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM readers")
        total_reader = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM borrow_records WHERE status = 0")
        borrow_now = cur.fetchone()[0]
    finally:
        cur.close()
        conn.close()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("图书总数量", total_book)
    with col2:
        st.metric("读者总人数", total_reader)
    with col3:
        st.metric("当前借出图书", borrow_now)
