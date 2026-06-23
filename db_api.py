import streamlit as st
from datetime import datetime
# 仅导入需求规定的基础函数，无拓展函数
from db_api import (
    add_book, search_book, update_book, delete_book,
    add_reader, search_reader, delete_reader,
    borrow_book, return_book,
    get_borrow_count, stock_by_category, get_book_ranking
)

st.set_page_config(page_title="图书馆管理系统", layout="wide")
st.title("图书馆管理系统")

# F12 侧边栏页面切换
menu = st.sidebar.selectbox("功能导航", ["图书管理", "读者管理", "借还操作", "数据统计"])

# F01-F04 图书管理
if menu == "图书管理":
    st.subheader("图书管理")
    tab1, tab2, tab3 = st.tabs(["新增图书F01", "查询/修改F02/F03", "删除图书F04"])
    with tab1:
        bid = st.text_input("书号")
        title = st.text_input("书名")
        author = st.text_input("作者")
        cid = st.text_input("分类编号")
        stock = st.number_input("库存", min_value=0)
        pub = st.text_input("出版社")
        if st.button("新增图书"):
            res = add_book(bid, title, author, cid, stock, pub)
            st.success("新增成功") if res else st.error("新增失败")
    with tab2:
        keyword = st.text_input("搜索图书")
        if st.button("查询"):
            st.dataframe(search_book(keyword))
        st.divider()
        edit_bid = st.text_input("待修改书号")
        new_title = st.text_input("新书名")
        new_author = st.text_input("新作者")
        new_cid = st.text_input("新分类")
        new_stock = st.number_input("新库存", min_value=0)
        new_pub = st.text_input("新出版社")
        if st.button("提交修改"):
            flag = update_book(edit_bid, new_title, new_author, new_cid, new_stock, new_pub)
            st.success("修改成功") if flag else st.error("修改失败")
    with tab3:
        del_bid = st.text_input("待删除书号")
        if st.button("删除图书", type="primary"):
            flag = delete_book(del_bid)
            st.success("删除成功") if flag else st.error("存在未归还记录，禁止删除")

# F05-F06 读者管理
elif menu == "读者管理":
    st.subheader("读者管理")
    tab1, tab2 = st.tabs(["新增读者F05", "查询/删除读者F06"])
    with tab1:
        rid = st.text_input("读者学号")
        name = st.text_input("姓名")
        cls = st.text_input("班级")
        phone = st.text_input("手机号")
        if st.button("新增读者"):
            flag = add_reader(rid, name, cls, phone)
            st.success("新增成功") if flag else st.error("学号重复")
    with tab2:
        key = st.text_input("搜索读者")
        if st.button("查询"):
            st.dataframe(search_reader(key))
        st.divider()
        del_rid = st.text_input("待删除学号")
        if st.button("删除读者", type="primary"):
            flag = delete_reader(del_rid)
            st.success("删除成功") if flag else st.error("该读者有未归还图书")

# F07-F08 借还操作
elif menu == "借还操作":
    st.subheader("图书借还")
    tab1, tab2 = st.tabs(["借书F07", "还书F08"])
    with tab1:
        b_bid = st.text_input("图书编号")
        b_rid = st.text_input("读者学号")
        if st.button("办理借书"):
            ok, msg = borrow_book(b_bid, b_rid)
            st.success(msg) if ok else st.error(msg)
    with tab2:
        rec_id = st.number_input("借阅记录ID", min_value=1)
        if st.button("办理还书"):
            ok, msg = return_book(rec_id)
            st.success(msg) if ok else st.error(msg)

# F09-F11 数据统计
elif menu == "数据统计":
    st.subheader("数据统计")
    # F09 未归还总数
    total = get_borrow_count()
    st.metric("当前未归还图书总数", total)
    st.divider()
    # F10 分类库存统计
    st.write("各分类库存统计F10")
    st.dataframe(stock_by_category())
    st.divider()
    # F11 借阅排行榜TOP5
    st.write("图书借阅排行榜F11")
    st.dataframe(get_book_ranking())
