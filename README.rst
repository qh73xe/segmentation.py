===========================
segmentation.py
===========================

基本的には Julius 音素セグメンテーションキット を python から使用しやすくしたものです．
ただし, 本家とは以下の点で差分があります.

1. ディレクトリ単位ではなくコマンド単位で操作:
    - 以下のように音声ファイルとその内容のペアで使用します.
    - :code:`python segmentation.py -i ./sample/sample.wav -t "きょうはいいてんきだ"`
2. 表記に関しては平仮名, カタカナ両方を許容:
    - IPU での記述に備え区切り文字 :code:`/` や :code:`_` などは除外するようにしました
    - :code:`python segmentation.py -i ./sample/sample.wav -t "キョウ/ワ/イイ/テンキ/ダ"`
3. その他, 表記ゆれに出来る限り対応:
    - 全角記号等は半角扱いにします
    - その他, unicode の表記揺れをある程度吸収します.
4. 重母音等の扱いを長音とした (例えば /おうさま/ を /おーさま/ と処理します)
5. 出力結果の音素表記は CSJ 分節音ラベル準拠:
    - https://pj.ninjal.ac.jp/corpus_center/csj/manu-f/segment.pdf
6. 入力する音声ファイルに関してはサンプリング周波数の制約はありません:
    - 中間ファイルを作成し，そこで julius 用にダウンサンプリングします
    - 中間ファイルは ~/.cache/julius 以下に作成されます
    - このディレクトリは存在しなければ勝手に作成されるはずです.
    - 解析終了後に中間ファイルは削除されます.
7. 音声ファイルがステレオの場合, 最初のチャンネルのみが解析対象になります:
    - これはその内オプションをつけるかもしれません.

Install
--------------------------

現状パッケージング等はしていないので，
./segmentation.py を直接利用してください．

各種依存関係に関しては以下のコマンドから解決可能です

.. code-block:: bash

   $ pip install -r ./requirements.txt

また, このスクリプトは Julius コマンドの薄いラッパーに過ぎないので，
julius コマンドが使用可能であることを確認してください.

.. code-block:: bash

   $ which julius
   /usr/local/bin/julius

また, 種々音声ファイルの取り扱いに ffmpeg を利用しているので,
これを導入しておく必要があるかもしれません.


.. code-block:: bash

   $  sudo dnf install ffmpeg ffmpeg-devel


使用方法
--------------------------

単純にコマンドラインから使用するには以下のようにします::

   $ python segmentation.py -i ./sample/sample.wav -t "きょうわいいてんきだ"
   [
       { "start": 0.0, "end": 0.23, "text": "#" },
       { "start": 0.23, "end": 0.32, "text": "ky" },
       { "start": 0.32, "end": 0.56, "text": "oH" },
       ...
       { "start": 1.58, "end": 2.04, "text": "#" }
   ]

出力結果を csv ファイルとして保存するには以下のコマンドを実行してください::

   $ python ./segmentation.py -i ./sample/sample.wav -t "きょうわいいてんきだ" -o sample.csv

同様に出力結果を TextGrid ファイルとして保存することも可能です::

   $ python ./segmentation.py -i ./sample/sample.wav -t "きょうわいいてんきだ" -o sample.TextGrid

出力結果の音素表記を julius のものにするには以下のオプションを与えてください::

   $ python ./segmentation.py -i ./sample/sample.wav -t "きょうわいいてんきだ" --voca

python からは以下のように使用します::

   from segmentation import Julius
   julius = Julius("./sample/sample.wav", "きょうわいいてんきだ")
   julius.run_segmentation()
   print(julius.result)
