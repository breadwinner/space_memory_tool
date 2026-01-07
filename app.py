import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, datetime, timedelta

# ==========================================
# 0. 数据库管理 (SQLite Backend)
# ==========================================
DB_FILE = "memory_system_v2.db"

def init_db():
    """初始化数据库表结构"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # 1. 卡片表
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
    
    # 2. 标签表 (用于下拉列表)
    c.execute('''
        CREATE TABLE IF NOT EXISTS tags (
            tag_name TEXT PRIMARY KEY
        )
    ''')
    
    # 初始化默认标签
    default_tags = ["Array", "BFS", "Binary Search", "DFS", "DP", "Graph", "Hash Table", "Two Pointers", "Stack", "Queue"]
    for tag in default_tags:
        try:
            c.execute("INSERT INTO tags VALUES (?)", (tag,))
        except sqlite3.IntegrityError:
            pass # 忽略重复

    # 初始化演示卡片数据
    c.execute("SELECT count(*) FROM cards")
    if c.fetchone()[0] == 0:
        demo_data = [
            ("217", "Contains Duplicate", "Array,Hash Table", 1, str(date.today()), str(date.today()), 0, 0, 2.5, 0, "https://leetcode.com/problems/contains-duplicate/"),
            ("200", "Number of Islands", "BFS,DFS", 3, str(date.today()), str(date.today()), 0, 0, 2.5, 0, "https://leetcode.com/problems/number-of-islands/"),
        ]
        c.executemany("INSERT INTO cards VALUES (?,?,?,?,?,?,?,?,?,?,?)", demo_data)
        conn.commit()
    
    conn.commit()
    conn.close()

def get_all_tags():
    """获取所有可用标签"""
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql("SELECT tag_name FROM tags ORDER BY tag_name", conn)
    conn.close()
    return df['tag_name'].tolist()

def create_new_tag(tag_name):
    """创建新标签"""
    if not tag_name: return False
    conn = sqlite3.connect(DB_FILE)
    try:
        conn.execute("INSERT INTO tags VALUES (?)", (tag_name,))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def load_data():
    """从数据库读取所有卡片"""
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql("SELECT * FROM cards", conn)
    conn.close()
    # 预处理数据
    df['next_review'] = pd.to_datetime(df['next_review']).dt.date
    df['last_review'] = pd.to_datetime(df['last_review']).dt.date
    df['tags_list'] = df['tags'].apply(lambda x: x.split(',') if x else [])
    return df

def update_card_progress(card_id, new_interval, new_reps, new_ef, next_date):
    """更新复习进度"""
    conn = sqlite3.connect(DB_FILE)
    conn.execute('''
        UPDATE cards 
        SET interval = ?, repetitions = ?, efactor = ?, next_review = ?, last_review = ?, review_count = review_count + 1
        WHERE id = ?
    ''', (new_interval, new_reps, new_ef, str(next_date), str(date.today()), card_id))
    conn.commit()
    conn.close()

def add_new_card(id, name, tags_list, stars, link, completion_date):
    """添加新卡片"""
    conn = sqlite3.connect(DB_FILE)
    tags_str = ",".join(tags_list)
    # 初始复习日期设为 "Completion Date"
    # 如果是补录以前的题，next_review 应该也是过去或者今天，这取决于你想不想立刻复习。
    # 这里逻辑设为：如果补录，next_review = completion_date (即如果你是很久以前做的，系统会立刻让你复习)
    try:
        conn.execute('''
            INSERT INTO cards (id, name, tags, stars, last_review, next_review, interval, repetitions, efactor, review_count, link)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (id, name, tags_str, stars, str(completion_date), str(completion_date), 0, 0, 2.5, 1, link))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def delete_card(card_id):
    """删除卡片"""
    conn = sqlite3.connect(DB_FILE)
    conn.execute("DELETE FROM cards WHERE id = ?", (card_id,))
    conn.commit()
    conn.close()

# 初始化
init_db()

# ==========================================
# 1. 样式与配置
# ==========================================
st.set_page_config(page_title="SR Memory System", layout="wide", page_icon="🧠")

st.markdown("""
<style>
    .stButton button { border-radius: 8px; }
    .tag-chip { display: inline-block; background-color: #E0E7FF; color: #4338CA; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; margin-right: 4px; font-weight: 500; }
    .star-yellow { color: #F59E0B; }
    .star-gray { color: #D1D5DB; }
    .row-container { border-bottom: 1px solid #f0f0f0; padding: 12px 0; align-items: center; }
    .delete-btn { color: #ef4444; cursor: pointer; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 算法 (SM-2)
# ==========================================
def calculate_sm2(row, quality):
    interval, repetitions, efactor = row['interval'], row['repetitions'], row['efactor']
    if quality < 3:
        repetitions = 0
        interval = 1
    else:
        if repetitions == 0: interval = 1
        elif repetitions == 1: interval = 6
        else: interval = int(interval * efactor)
        repetitions += 1
        efactor = max(1.3, efactor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
    return interval, repetitions, efactor, date.today() + timedelta(days=interval)

def render_stars(count):
    return "".join([f'<span class="star-yellow">★</span>' if i < count else f'<span class="star-gray">★</span>' for i in range(5)])

def render_tags(tag_list):
    return "".join([f'<span class="tag-chip">{tag}</span>' for tag in tag_list])

# ==========================================
# 3. 主界面
# ==========================================
df = load_data()

# Header
c1, c2 = st.columns([3, 1])
with c1:
    st.title("Spaced-Repetition Memory System")
with c2:
    today_due = len(df[df['next_review'] <= date.today()])
    st.metric("Due Today", f"{today_due}", delta=f"Total: {len(df)}")

tabs = st.tabs(["Today's Review", "Library & Manage"])

# --- Tab 1: Review ---
with tabs[0]:
    due_df = df[df['next_review'] <= date.today()]
    if due_df.empty:
        st.success("🎉 All caught up!")
    else:
        st.caption("Rate your memory recall (1: Blackout -> 5: Perfect)")
        st.markdown("---")
        for _, row in due_df.iterrows():
            c1, c2, c3, c4, c5 = st.columns([1, 3, 2, 3, 1])
            with c1: st.markdown(f"**{row['id']}**")
            with c2: st.markdown(f"[{row['name']}]({row['link']})")
            with c3: st.markdown(render_tags(row['tags_list']), unsafe_allow_html=True)
            with c4:
                cols = st.columns(5)
                for i in range(1, 6):
                    if cols[i-1].button(f"{i}", key=f"rev_{row['id']}_{i}", use_container_width=True):
                        i_new, r_new, ef_new, d_new = calculate_sm2(row, i)
                        update_card_progress(row['id'], i_new, r_new, ef_new, d_new)
                        st.toast(f"Reviewed {row['id']}!")
                        st.rerun()
            with c5: st.caption(f"x{row['review_count']}")
            st.markdown("<div class='row-container'></div>", unsafe_allow_html=True)

# --- Tab 2: Library & Add ---
with tabs[1]:
    
    # === Add New Card Section ===
    with st.expander("➕ Add New Card", expanded=False):
        c_left, c_right = st.columns([2, 1])
        
        with c_left:
            with st.form("add_card_form", clear_on_submit=True):
                st.subheader("Add New Card")
                
                # Link (Optional)
                link = st.text_input("LeetCode Link (Optional)", placeholder="https://leetcode.com/problems/...")
                
                # ID & Name
                c_id, c_name = st.columns([1, 3])
                card_id = c_id.text_input("Problem ID *", placeholder="e.g., 217")
                card_name = c_name.text_input("Problem Name", placeholder="e.g., Contains Duplicate")
                
                # Date & Stars
                c_date, c_stars = st.columns([1, 1])
                comp_date = c_date.date_input("Completion Date", value=date.today())
                stars = c_stars.slider("Difficulty Rating", 1, 5, 3)
                
                # Tags - Dropdown
                all_tags = get_all_tags()
                selected_tags = st.multiselect("Tags (Select)", options=all_tags)
                
                submitted = st.form_submit_button("Save Card", type="primary")
                
                if submitted:
                    if not card_id or not card_name:
                        st.error("Problem ID and Name are required!")
                    else:
                        if add_new_card(card_id, card_name, selected_tags, stars, link, comp_date):
                            st.success(f"Added {card_name}!")
                            st.rerun()
                        else:
                            st.error(f"Card ID {card_id} already exists!")

        # Create New Tag Section (Right Side)
        with c_right:
            st.markdown("<br><br>", unsafe_allow_html=True) # Spacer
            st.info("💡 Missing a tag?")
            new_tag_input = st.text_input("Create New Tag", placeholder="e.g., Backtracking")
            if st.button("Create Tag"):
                if create_new_tag(new_tag_input):
                    st.success(f"Tag '{new_tag_input}' created!")
                    st.rerun()
                else:
                    st.warning("Tag already exists or invalid.")

    st.markdown("---")

    # === Library List Section ===
    st.subheader(f"Library ({len(df)})")
    
    # Filters
    f_col1, f_col2 = st.columns([3, 1])
    search = f_col1.text_input("🔍 Search", placeholder="Search by ID, Name...")
    
    view_df = df.copy()
    if search:
        mask = view_df.apply(lambda x: search.lower() in str(x).lower(), axis=1)
        view_df = view_df[mask]

    # Render List
    # Header Row
    h1, h2, h3, h4, h5, h6 = st.columns([1, 2, 3, 2, 2, 1])
    h1.markdown("**Stars**")
    h2.markdown("**ID**")
    h3.markdown("**Name**")
    h4.markdown("**Tags**")
    h5.markdown("**Last Review**")
    h6.markdown("**Action**")
    st.divider()

    # Data Rows
    for _, row in view_df.iterrows():
        c1, c2, c3, c4, c5, c6 = st.columns([1, 2, 3, 2, 2, 1])
        
        with c1: st.markdown(render_stars(row['stars']), unsafe_allow_html=True)
        with c2: st.code(row['id'], language=None)
        with c3: st.markdown(f"[{row['name']}]({row['link']})")
        with c4: st.markdown(render_tags(row['tags_list']), unsafe_allow_html=True)
        with c5: st.write(row['last_review'])
        with c6:
            # DELETE BUTTON
            if st.button("🗑", key=f"del_{row['id']}", help="Delete this card"):
                delete_card(row['id'])
                st.toast(f"Deleted {row['id']}")
                st.rerun()
        
        st.markdown("<div class='row-container'></div>", unsafe_allow_html=True)
