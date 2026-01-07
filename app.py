import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, datetime, timedelta
import uuid

# ==========================================
# 0. 数据库管理 (SQLite Backend)
# ==========================================
DB_FILE = "memory_system.db"

def init_db():
    """初始化数据库表结构"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # 创建主表
    c.execute('''
        CREATE TABLE IF NOT EXISTS cards (
            id TEXT PRIMARY KEY,
            name TEXT,
            tags TEXT,
            stars INTEGER,
            last_review TEXT,
            next_review TEXT,
            interval INTEGER,
            repetitions INTEGER,
            efactor REAL,
            review_count INTEGER,
            link TEXT
        )
    ''')
    
    # 如果是空表，插入之前的演示数据
    c.execute("SELECT count(*) FROM cards")
    if c.fetchone()[0] == 0:
        demo_data = [
            ("search-rotated", "Search In Rotated Sorted Array", "Binary Search,Array", 3, "2026-01-01", str(date.today()), 1, 0, 2.5, 1, "https://leetcode.com"),
            ("kth-smallest", "Kth Smallest Element In A BST", "Tree,DFS", 4, "2026-01-02", str(date.today()), 1, 0, 2.5, 1, "https://leetcode.com"),
            ("clone-graph", "Clone Graph", "Graph,BFS", 3, "2026-01-05", str(date.today()), 1, 0, 2.5, 1, "https://leetcode.com"),
            ("rotting-oranges", "Rotting Oranges", "BFS,Matrix", 3, "2025-12-30", "2026-01-06", 3, 1, 2.6, 2, "https://leetcode.com"),
        ]
        c.executemany("INSERT INTO cards VALUES (?,?,?,?,?,?,?,?,?,?,?)", demo_data)
        conn.commit()
    
    conn.close()

def load_data():
    """从数据库读取所有数据到 DataFrame"""
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql("SELECT * FROM cards", conn)
    conn.close()
    # 转换日期列格式
    df['next_review'] = pd.to_datetime(df['next_review']).dt.date
    # 简单的 Tag 字符串转列表处理 (为了 UI 显示)
    df['tags_list'] = df['tags'].apply(lambda x: x.split(',') if x else [])
    return df

def update_card_progress(card_id, new_interval, new_reps, new_ef, next_date):
    """更新卡片复习进度"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        UPDATE cards 
        SET interval = ?, repetitions = ?, efactor = ?, next_review = ?, last_review = ?, review_count = review_count + 1
        WHERE id = ?
    ''', (new_interval, new_reps, new_ef, str(next_date), str(date.today()), card_id))
    conn.commit()
    conn.close()

def add_new_card(id, name, tags, stars, link):
    """插入新卡片"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO cards (id, name, tags, stars, last_review, next_review, interval, repetitions, efactor, review_count, link)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (id, name, tags, stars, str(date.today()), str(date.today()), 0, 0, 2.5, 0, link))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

# 初始化数据库
init_db()

# ==========================================
# 1. 配置与样式 (CSS Styling)
# ==========================================
st.set_page_config(page_title="SR Memory System", layout="wide", page_icon="🧠")

st.markdown("""
<style>
    .metric-container { display: flex; justify-content: flex-end; align-items: center; padding: 10px; font-family: 'Arial', sans-serif; }
    .metric-item { margin-left: 20px; text-align: center; }
    .metric-value { font-size: 1.2rem; font-weight: bold; color: #4F46E5; }
    .metric-label { font-size: 0.8rem; color: #666; }
    .tag-chip { display: inline-block; background-color: #E0E7FF; color: #4338CA; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; margin-right: 4px; font-weight: 500; }
    .star-yellow { color: #F59E0B; }
    .star-gray { color: #D1D5DB; }
    .row-container { border-bottom: 1px solid #f0f0f0; padding: 10px 0; align-items: center; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 核心逻辑 (SM-2 Algorithm)
# ==========================================

def calculate_sm2(row, quality):
    """计算 SM-2 算法的新状态 (纯逻辑，不操作DB)"""
    interval = row['interval']
    repetitions = row['repetitions']
    efactor = row['efactor']
    
    if quality < 3:
        repetitions = 0
        interval = 1
    else:
        if repetitions == 0:
            interval = 1
        elif repetitions == 1:
            interval = 6
        else:
            interval = int(interval * efactor)
        
        repetitions += 1
        efactor = efactor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        if efactor < 1.3: efactor = 1.3

    next_review_date = date.today() + timedelta(days=interval)
    return interval, repetitions, efactor, next_review_date

def handle_review_click(row, quality):
    """处理点击事件"""
    new_int, new_rep, new_ef, new_date = calculate_sm2(row, quality)
    update_card_progress(row['id'], new_int, new_rep, new_ef, new_date)
    st.toast(f"✅ Reviewed: {row['id']} -> Next: {new_date}")
    # 强制刷新页面以获取最新数据
    st.rerun()

def render_stars(count):
    return "".join([f'<span class="star-yellow">★</span>' if i < count else f'<span class="star-gray">★</span>' for i in range(5)])

def render_tags(tag_list):
    return "".join([f'<span class="tag-chip">{tag}</span>' for tag in tag_list])

# ==========================================
# 3. 页面布局
# ==========================================

# 加载实时数据
df = load_data()

# Header
col_h1, col_h2 = st.columns([2, 1])
with col_h1:
    st.title("Spaced-Repetition Memory System")
    st.caption("Local Database: SQLite")
with col_h2:
    today_due = len(df[df['next_review'] <= date.today()])
    st.markdown(f"""
    <div class="metric-container">
        <div class="metric-item"><div class="metric-label">Due Today</div><div class="metric-value" style="color: #e11d48;">{today_due}</div></div>
        <div class="metric-item"><div class="metric-label">Total Cards</div><div class="metric-value">{len(df)}</div></div>
    </div>
    """, unsafe_allow_html=True)

tab_review, tab_library = st.tabs(["Today's Review", "Library"])

# --- Tab 1: 复习界面 ---
with tab_review:
    c1, c2 = st.columns([4, 1])
    with c1:
        st.info(f"📅 Today is {date.today()}. You have **{today_due}** cards to review.")
    
    st.divider()

    due_df = df[df['next_review'] <= date.today()]

    if due_df.empty:
        st.success("🎉 You are all caught up!")
    else:
        # 表头
        cols = st.columns([1, 2, 3, 2, 3, 1])
        headers = ["Stars", "ID", "Name", "Tags", "Quality (1-5)", "Count"]
        for col, h in zip(cols, headers): col.markdown(f"**{h}**")
        st.divider()

        for idx, row in due_df.iterrows():
            c1, c2, c3, c4, c5, c6 = st.columns([1, 2, 3, 2, 3, 1])
            with c1: st.markdown(render_stars(row['stars']), unsafe_allow_html=True)
            with c2: st.code(row['id'], language=None)
            with c3: st.write(f"[{row['name']}]({row['link']})")
            with c4: st.markdown(render_tags(row['tags_list']), unsafe_allow_html=True)
            with c5:
                # 评分按钮
                b_cols = st.columns(5)
                for i in range(1, 6):
                    if b_cols[i-1].button(f"{i}", key=f"btn_{row['id']}_{i}"):
                        handle_review_click(row, i)
            with c6: st.caption(f"{row['review_count']} times")
            st.markdown("<div class='row-container'></div>", unsafe_allow_html=True)

# --- Tab 2: 题库管理 (支持添加) ---
with tab_library:
    # 添加新卡片的功能区 (Expander)
    with st.expander("➕ Add New Card", expanded=False):
        with st.form("add_card_form"):
            c1, c2 = st.columns(2)
            new_id = c1.text_input("ID (e.g. two-sum)")
            new_name = c2.text_input("Name (e.g. Two Sum)")
            c3, c4 = st.columns(2)
            new_tags = c3.text_input("Tags (comma separated)", "Array,Hash Table")
            new_link = c4.text_input("Link", "https://leetcode.com/problems/...")
            new_stars = st.slider("Difficulty Stars", 1, 5, 3)
            
            submitted = st.form_submit_button("Save Card")
            if submitted:
                if new_id and new_name:
                    success = add_new_card(new_id, new_name, new_tags, new_stars, new_link)
                    if success:
                        st.success(f"Added {new_id} successfully!")
                        st.rerun()
                    else:
                        st.error(f"ID '{new_id}' already exists!")
                else:
                    st.warning("ID and Name are required.")

    st.divider()
    
    # 搜索与展示
    search_q = st.text_input("🔍 Search Library", placeholder="Search by ID, Name or Tags")
    
    display_df = df.copy()
    if search_q:
        mask = display_df.apply(lambda x: search_q.lower() in str(x['id']).lower() or search_q.lower() in str(x['name']).lower() or search_q.lower() in str(x['tags']).lower(), axis=1)
        display_df = display_df[mask]

    st.dataframe(
        display_df,
        column_config={
            "stars": st.column_config.NumberColumn("Stars", format="%d ⭐"),
            "link": st.column_config.LinkColumn("Link", display_text="Open"),
            "tags": "Tags",
            "next_review": st.column_config.DateColumn("Next Review", format="YYYY-MM-DD"),
            "last_review": st.column_config.DateColumn("Last Review", format="YYYY-MM-DD"),
            "efactor": st.column_config.NumberColumn("E-Factor", format="%.2f"),
        },
        column_order=("stars", "id", "name", "tags", "next_review", "last_review", "review_count", "efactor", "link"),
        use_container_width=True,
        hide_index=True
    )
