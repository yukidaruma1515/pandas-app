import os
import fcntl
from datetime import datetime

import pandas as pd
import streamlit as st


FILE_NAME = "lesson2_exercise_log.csv"
COLUMNS = ["日時", "わからなかった項目", "理解度"]

topics = [
    "演習問題1-1: CSV読み込みとDataFrame表示",
    "演習問題1-2: 先頭3行の表示",
    "演習問題2-1: locで国語と英語を抽出",
    "演習問題2-2: 学年3かつ数学85点以上を抽出",
    "演習問題2-3: 国語または英語95点以上を抽出",
    "演習問題3-1: 要約統計量の表示",
    "演習問題3-2: 欠損値を含む行の表示",
    "演習問題3-3: 学校別の人数と統計量",
    "演習問題4-1: 国語のヒストグラム作成",
    "演習問題4-2: 英語と数学の散布図作成",
    "その他",
]


def ensure_csv():
    if not os.path.exists(FILE_NAME):
        pd.DataFrame(columns=COLUMNS).to_csv(FILE_NAME, index=False, encoding="utf-8-sig")


def normalize_log(df):
    for column in COLUMNS:
        if column not in df.columns:
            df[column] = None

    return df[COLUMNS]


def read_log():
    ensure_csv()
    with open(FILE_NAME, "r", encoding="utf-8-sig") as file:
        fcntl.flock(file, fcntl.LOCK_SH)
        try:
            return normalize_log(pd.read_csv(file))
        finally:
            fcntl.flock(file, fcntl.LOCK_UN)


def save_answers(topic_levels):
    ensure_csv()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = pd.DataFrame(
        {
            "日時": [now for _ in topic_levels],
            "わからなかった項目": list(topic_levels.keys()),
            "理解度": list(topic_levels.values()),
        }
    )

    with open(FILE_NAME, "r+", encoding="utf-8-sig") as file:
        fcntl.flock(file, fcntl.LOCK_EX)
        try:
            current = normalize_log(pd.read_csv(file))
            updated = pd.concat([current, rows], ignore_index=True)
            file.seek(0)
            file.truncate()
            updated.to_csv(file, index=False)
        finally:
            fcntl.flock(file, fcntl.LOCK_UN)


def create_summary(df):
    df = df.copy()
    df["理解度"] = pd.to_numeric(df["理解度"], errors="coerce")

    topic_count = df["わからなかった項目"].value_counts()
    avg_level = df.groupby("わからなかった項目")["理解度"].mean()
    low_level_count = df[df["理解度"] <= 2]["わからなかった項目"].value_counts()

    summary = pd.DataFrame(
        {
            "わからなかった人数": topic_count,
            "平均理解度": avg_level,
            "理解度1から2の人数": low_level_count,
        }
    ).fillna(0)

    summary["補足優先度"] = summary["わからなかった人数"] * (6 - summary["平均理解度"])
    return summary.sort_values("補足優先度", ascending=False)


def show_bar_chart(series, title):
    chart_data = series.sort_values(ascending=False).rename(title)
    st.bar_chart(chart_data)


st.set_page_config(page_title="わからないログ", layout="wide")
st.title("第2回授業 演習問題 わからなかった問題 可視化アプリ")

tab_input, tab_summary = st.tabs(["入力", "集計"])

with tab_input:
    st.subheader("回答入力")
    with st.form("wakaranai_form", clear_on_submit=True):
        st.write("わからなかった問題にチェックして、理解度を選んでください。")
        topic_levels = {}

        for topic in topics:
            topic_col, level_col = st.columns([3, 2])
            selected = topic_col.checkbox(topic, key=f"selected_{topic}")
            with level_col:
                level = st.slider(
                    "理解度",
                    min_value=1,
                    max_value=5,
                    value=3,
                    key=f"level_{topic}",
                    label_visibility="collapsed",
                )

            if selected:
                topic_levels[topic] = level

        submitted = st.form_submit_button("記録する")

    if submitted:
        if not topic_levels:
            st.warning("項目を1つ以上選んでください。")
        else:
            save_answers(topic_levels)
            st.success("記録しました。")

with tab_summary:
    df = read_log()

    if df.empty:
        st.info("まだデータがありません。")
    else:
        summary = create_summary(df)
        top_topic = summary.index[0]
        top_avg = summary.loc[top_topic, "平均理解度"]

        col1, col2, col3 = st.columns(3)
        col1.metric("記録数", len(df))
        col2.metric("最も補足が必要な項目", top_topic)
        col3.metric("平均理解度", round(top_avg, 2))

        st.subheader("集計結果")
        st.dataframe(summary, use_container_width=True)

        st.subheader("自動コメント")
        st.write(f"最も補足が必要そうな項目は「{top_topic}」です。")

        if top_avg <= 2:
            st.write("この項目は理解度が低いため、例題を使った説明が必要そうです。")
        elif top_avg <= 3:
            st.write("この項目は少しつまずいている人が多いため、復習すると効果がありそうです。")
        else:
            st.write("理解度は極端に低くありませんが、選んだ人が多いため確認問題を行うとよさそうです。")

        graph_col1, graph_col2 = st.columns(2)
        with graph_col1:
            st.subheader("わからなかった人数ランキング")
            show_bar_chart(summary["わからなかった人数"], "人数")
        with graph_col2:
            st.subheader("補足説明が必要そうな項目")
            show_bar_chart(summary["補足優先度"], "補足優先度")

        st.subheader("項目別の平均理解度")
        show_bar_chart(summary["平均理解度"], "平均理解度")

        csv_data = df.to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            "CSVをダウンロード",
            data=csv_data.encode("utf-8-sig"),
            file_name=FILE_NAME,
            mime="text/csv",
        )
