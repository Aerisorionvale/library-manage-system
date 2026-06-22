import streamlit as st
from db_api import get_conn
import pandas as pd

# 页面基础配置
st.set_page_config(page_title="图书管理系统", layout="wide")
st.title("📚 图书管理系统（TiDB云端版）")

# 获取数据库连接
conn = get_conn()
cur = conn.cursor()

# 侧边栏功能导航
menu = st.sidebar.selectbox("功能菜单", ["图书查询", "新增图书", "读者管理", "借阅管理", "数据统计"])

# 1.图书查询模块
if menu == "图书查询":
    st.subheader("图书信息查询")
    search_key = st.text_input("输入图书名称/编号搜索")
    if st.button("查询"):
        if search_key:
            sql = f"""
            SELECT b.book_id 图书编号,b.title 书名,b.author 作者,c.category_name 分类,
                   b.stock 库存,b.publisher 出版社
            FROM books b LEFT JOIN category c ON b.category_id = c.category_id
            WHERE b.book_id LIKE '%{search_key}%' OR b.title LIKE '%{search_key}%'
            """
        else:
            sql = """
            SELECT b.book_id 图书编号,b.title 书名,b.author 作者,c.category_name 分类,
                   b.stock 库存,b.publisher 出版社
            FROM books b LEFT JOIN category c ON b.category_id = c.category_id
            """
        cur.execute(sql)
        res = cur.fetchall()
        col = [i[0] for i in cur.description]
        df = pd.DataFrame(res, columns=col)
        st.dataframe(df, use_container_width=True)

# 2.新增图书模块
elif menu == "新增图书":
    st.subheader("添加新图书")
    c_sql = "SELECT category_id,category_name FROM category"
    cur.execute(c_sql)
    cate_list = cur.fetchall()
    cate_dict = {i[1]: i[0] for i in cate_list}
    cate_name = st.selectbox("图书分类", list(cate_dict.keys()))
    book_id = st.text_input("图书编号")
    title = st.text_input("图书名称")
    author = st.text_input("作者")
    stock = st.number_input("库存数量", min_value=1, value=1)
    pub = st.text_input("出版社")
    if st.button("提交新增"):
        cid = cate_dict[cate_name]
        insert_sql = """
        INSERT INTO books(book_id,title,author,category_id,stock,publisher)
        VALUES(%s,%s,%s,%s,%s,%s)
        """
        try:
            cur.execute(insert_sql, (book_id, title, author, cid, stock, pub))
            conn.commit()
            st.success("图书新增成功！")
        except Exception as e:
            conn.rollback()
            st.error(f"新增失败：{e}")

# 3.读者管理模块
elif menu == "读者管理":
    tab1, tab2 = st.tabs(["读者列表", "新增读者"])
    with tab1:
        cur.execute("SELECT * FROM readers")
        reader_data = cur.fetchall()
        reader_col = [i[0] for i in cur.description]
        st.dataframe(pd.DataFrame(reader_data, columns=reader_col), use_container_width=True)
    with tab2:
        rid = st.text_input("读者编号")
        rname = st.text_input("读者姓名")
        rtype = st.selectbox("读者类型", ["学生", "教师"])
        phone = st.text_input("联系电话")
        if st.button("添加读者"):
            ins_sql = "INSERT INTO readers(reader_id,reader_name,reader_type,phone) VALUES(%s,%s,%s,%s)"
            try:
                cur.execute(ins_sql, (rid, rname, rtype, phone))
                conn.commit()
                st.success("读者添加完成")
            except Exception as e:
                conn.rollback()
                st.error(f"失败：{e}")

# 4.借阅管理模块
elif menu == "借阅管理":
    tab1, tab2 = st.tabs(["借阅记录", "图书借阅"])
    with tab1:
        borrow_sql = """
        SELECT br.record_id, r.reader_name 读者, b.title 图书, br.borrow_date 借出日期,
               br.due_date 应还日期, br.return_date 归还日期, br.status
        FROM borrow_records br
        LEFT JOIN readers r ON br.reader_id = r.reader_id
        LEFT JOIN books b ON br.book_id = b.book_id
        """
        cur.execute(borrow_sql)
        borrow_data = cur.fetchall()
        borrow_col = [i[0] for i in cur.description]
        st.dataframe(pd.DataFrame(borrow_data, columns=borrow_col), use_container_width=True)
    with tab2:
        cur.execute("SELECT reader_id,reader_name FROM readers")
        r_all = cur.fetchall()
        r_select = {f"{i[0]} {i[1]}": i[0] for i in r_all}
        sel_r = st.selectbox("选择读者", list(r_select.keys()))
        cur.execute("SELECT book_id,title FROM books WHERE stock>0")
        b_all = cur.fetchall()
        b_select = {f"{i[0]} {i[1]}": i[0] for i in b_all}
        sel_b = st.selectbox("选择借阅图书", list(b_select.keys()))
        due_day = st.number_input("借阅天数", min_value=7, value=30)
        if st.button("确认借阅"):
            rid = r_select[sel_r]
            bid = b_select[sel_b]
            borrow_sql = """
            INSERT INTO borrow_records(reader_id,book_id,borrow_date,due_date,status)
            VALUES(%s,%s,CURRENT_DATE(),DATE_ADD(CURRENT_DATE(),INTERVAL %s DAY),0)
            """
            stock_sql = "UPDATE books SET stock=stock-1 WHERE book_id=%s"
            try:
                cur.execute(borrow_sql, (rid, bid, due_day))
                cur.execute(stock_sql, (bid,))
                conn.commit()
                st.success("借阅登记成功！")
            except Exception as e:
                conn.rollback()
                st.error(f"操作失败：{e}")

# 5.数据统计模块
elif menu == "数据统计":
    st.subheader("系统数据统计")
    cur.execute("SELECT COUNT(*) FROM books")
    book_total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM readers")
    reader_total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM borrow_records WHERE status=0")
    borrow_out = cur.fetchone()[0]
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("图书总数量", book_total)
    with col2:
        st.metric("读者总数", reader_total)
    with col3:
        st.metric("当前借出图书", borrow_out)

# 关闭游标与连接
cur.close()
conn.close()
