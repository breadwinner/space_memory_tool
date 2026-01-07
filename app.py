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
        efactor = max(1.3, efactor + (0.1 - (5 - quality) * (0.08 + (5 -
