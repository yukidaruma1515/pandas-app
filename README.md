# 授業のわからなかった項目 可視化アプリ

Googleフォームを使わず、Streamlitだけで第2回授業の演習問題について回答の入力、CSV保存、集計、可視化を行うWebアプリです。

## できること

- わからなかった演習問題を複数選択
- 選択した問題ごとに理解度を1から5で記録
- CSVに自動保存
- わからなかった人数、平均理解度、補足優先度を集計
- 棒グラフで可視化
- CSVをダウンロード

## ローカルでの起動

第2回授業用アプリ:

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

第3回授業用アプリ:

```bash
pip install -r requirements.txt
streamlit run lesson3_streamlit_app.py
```

同じWi-Fi内の端末から入力してもらう場合は、次のように起動します。

```bash
streamlit run streamlit_app.py --server.address 0.0.0.0
```

第3回授業用アプリを共有する場合は、次のように起動します。

```bash
streamlit run lesson3_streamlit_app.py --server.address 0.0.0.0
```

起動後に表示される `Network URL` を回答者に共有してください。

## データについて

第2回授業用アプリの回答データは `lesson2_exercise_log.csv` に保存されます。
第3回授業用アプリの回答データは `lesson3_exercise_log.csv` に保存されます。
これらのファイルは個人情報や授業データを含む可能性があるため、GitHubには上げない設定にしています。

アプリ起動時に回答CSVがなければ自動作成されます。

## Streamlit Community Cloudで使う場合の注意

GitHubにこのコードを上げればStreamlit Community Cloudで公開できます。ただし、無料のクラウド環境ではアプリ内で作成したCSVが永続保存されない場合があります。

授業中に一時的に集める用途なら使えます。長期保存したい場合は、Googleスプレッドシート、Supabase、SQLiteを置けるサーバーなど、外部の保存先を使う必要があります。
