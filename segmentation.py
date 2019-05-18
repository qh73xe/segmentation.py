# -*- coding: utf-8 -*
"""Julius を使用した自動アノテーションコマンドを発行します"""
from os import path


class Julius(object):
    """Julius 音素アラインメントを実行します.

    >>> julius = Julius("sample/sample.wav", "きょうわいいてんきだ")
    >>> julius.run_segmentation()
    >>> " ".join([x["text"] for x in julius.result])
    'silB ky o: w a i: t e N k i d a silE'
    >>> " ".join([str(x["start"]) for x in julius.result])
    '0.0 0.23 0.32 0.56 0.68 0.76 0.98 1.07 1.17 1.27 1.39 1.44 1.5 1.6'
    >>> " ".join([str(x["end"]) for x in julius.result])
    '0.23 0.32 0.56 0.68 0.76 0.98 1.07 1.17 1.27 1.39 1.44 1.5 1.6 2.04'
    """
    cdir = None
    bname = None
    wav = None
    dic = None
    dfa = None
    model = None
    result = None
    row = None

    def __init__(self, wav, text, model=None):
        self.check_cache()
        self.wav = wav
        self.bname, _ = path.splitext(path.basename(wav))
        self.create_text_info(text)
        if model:
            self.model = model
        else:
            self.model = path.join(
                path.dirname(path.abspath(__file__)), "models",
                "hmmdefs_monof_mix16_gid.binhmm"
            )

    def check_cache(self):
        """キャッシュファイル保存用のディレクトリを確認.

        存在しない場合作成を行います
        """
        home = path.expanduser("~")
        cdir = path.join(home, ".cache", "julius")
        if not path.exists(cdir):
            from os import makedirs
            makedirs(cdir)
        self.cdir = cdir

    def create_text_info(self, text):
        """julius のセグメンテーションに必要なファイルを生成します"""
        dic_path = path.join(self.cdir, "{}.dict".format(self.bname))
        dic = create_dict(text)
        with open(dic_path, mode='w') as f:
            f.write("\n".join(dic))
        self.dic = dic_path

        dfa_path = path.join(self.cdir, "{}.dfa".format(self.bname))
        dfa = create_dfa(dic)
        with open(dfa_path, mode='w') as f:
            f.write("\n".join(dfa))
        self.dfa = dfa_path

    def run_segmentation(self, csj=True):
        proc = run_julius(self.wav, self.model, self.dfa, self.dic)
        self.result = []
        self.row = proc.communicate()[0]
        try:
            res = self.row.split("\n")
            s_index = res.index("=== begin forced alignment ===")
            e_index = res.index("=== end forced alignment ===")
            segmentations = [
                [
                    x for x in l.replace("[", "").replace("]", "").split(" ")
                    if x
                ] for l in res[s_index:e_index] if "[" in l
            ]
            for i, items in enumerate(segmentations):
                s_time = round(int(items[0]) * 0.01, 2)
                e_time = round((int(items[1]) + 1) * 0.01, 2)
                text = items[-1]
                if csj:
                    if i != len(segmentations) - 1:
                        text = voca2csj(
                            items[-1], next_seg=segmentations[i + 1]
                        )
                    else:
                        text = voca2csj(items[-1])
                item = {
                    "start": s_time,
                    "end": e_time,
                    "text": text,
                }
                self.result.append(item)
        except Exception:
            pass

    def to_csv(self, output):
        import os
        from pandas import DataFrame
        df = DataFrame(self.result)
        if os.name == "nt":
            df.to_csv(output, index=False, encoding="cp932")
        else:
            df.to_csv(output, index=False)


def run_julius(wav, model, dfa, dic):
    from subprocess import Popen, PIPE, STDOUT
    cmds = [
        "julius", "-h", model, "-dfa", dfa, "-v", dic, "-palign", "-input",
        "file"
    ]
    proc = Popen(["echo", wav], stdout=PIPE, stderr=STDOUT)
    proc2 = Popen(
        cmds,
        stdin=proc.stdout,
        stdout=PIPE,
        stderr=STDOUT,
        universal_newlines=True
    )
    return proc2


def create_dict(text):
    """平仮名を julius dict 形式に変換します.
    >>> create_dict("きょうわいいてんきだ")
    ['0 [w_0] silB', '1 [w_1] ky o: w a i: t e N k i d a', '2 [w_2] silE']
    """
    works = ["silB"]
    works.append(yomi2voca(text))
    works.append("silE")
    return ["{i} [w_{i}] {t}".format(i=i, t=t) for i, t in enumerate(works)]


def create_dfa(julius_dic):
    """julisu dict から dfa を生成します

    >>> dic = create_dict("きょうわいいてんきだ")
    >>> create_dfa(dic)
    ['0 2 1 0 1', '1 1 2 0 0', '2 0 3 0 0', '3 -1 -1 1 0']
    """
    num = len(julius_dic)
    dfas = []
    for i in range(num):
        s = "{} {} {} 0".format(i, num - i - 1, i + 1)
        if (i == 0):
            s = s + " 1"
        else:
            s = s + " 0"
        dfas.append(s)
    dfas.append("{} -1 -1 1 0".format(num))
    return dfas


def voca2csj(seg, next_seg=None):
    """julius voca 形式を CSJ 分節音ラベルに変換します."""
    if "sil" in seg:
        return "#"
    if ":" in seg:
        return seg.replace(":", "H")
    if (seg == "q"):
        return "Q"
    if (seg == "ts"):
        return "c"
    if (seg == "f") & (next_seg == "u"):
        return "F"
    if (seg == "f") & (next_seg == "u:"):
        return "F"
    if (seg == "k") & ("i" in next_seg):
        return "kj"
    if (seg == "g") & ("i" in next_seg):
        return "gj"
    if (seg == "sh") & ("i" in next_seg):
        return "sj"
    if (seg == "j") & ("i" in next_seg):
        return "zj"
    if (seg == "ch") & ("i" in next_seg):
        return "cj"
    if (seg == "n") & ("i" in next_seg):
        return "nj"
    if (seg == "h") & ("i" in next_seg):
        return "hj"
    if (seg == "sh"):
        return "sy"
    if (seg == "ch") & ("a" in next_seg):
        return "cy"
    if (seg == "ch") & ("u" in next_seg):
        return "cy"
    if (seg == "ch") & ("o" in next_seg):
        return "cy"
    if (seg == "hy") & ("a" in next_seg):
        return "Fy"
    if (seg == "hy") & ("u" in next_seg):
        return "Fy"
    if (seg == "hy") & ("o" in next_seg):
        return "Fy"
    return seg


def yomi2voca(text):
    """平仮名を julius voca 形式に変換します.

    >>> yomi2voca("きょうわいいてんきだ")
    'ky o: w a i: t e N k i d a'

    """
    import re
    import jaconv
    # 文字列正規化処理
    text = text.strip()
    text = jaconv.normalize(text, "NFKC")
    text = jaconv.kata2hira(text)

    # 3 文字以上からなる変換規則
    text = re.sub('う゛ぁ', ' b a', text)
    text = re.sub('う゛ぃ', ' b i', text)
    text = re.sub('う゛ぇ', ' b e', text)
    text = re.sub('う゛ぉ', ' b o', text)
    text = re.sub('う゛ゅ', ' by u', text)

    text = re.sub('きょう', ' ky o:', text)
    text = re.sub('きょお', ' ky o:', text)
    text = re.sub('きゅう', ' ky u:', text)

    # 2 文字からなる変換規則
    text = re.sub("ぅ゛", " b u", text)
    text = re.sub("あぁ", " a:", text)
    text = re.sub("ああ", " a:", text)
    text = re.sub("いぃ", " i:", text)
    text = re.sub("いい", " i:", text)
    text = re.sub("いぇ", " i e", text)
    text = re.sub("いゃ", " y a", text)
    text = re.sub("うう", " u:", text)
    text = re.sub("うぅ", " u:", text)
    text = re.sub("ええ", " e:", text)
    text = re.sub("えぇ", " e:", text)
    text = re.sub("おお", " o:", text)
    text = re.sub("おう", " o:", text)
    text = re.sub("おぉ", " o:", text)
    text = re.sub("かぁ", " k a:", text)
    text = re.sub("かあ", " k a:", text)
    text = re.sub("きぃ", " k i:", text)
    text = re.sub("きい", " k i:", text)
    text = re.sub("くぅ", " k u:", text)
    text = re.sub("くう", " k u:", text)
    text = re.sub("くゃ", " ky a", text)
    text = re.sub("くゅ", " ky u", text)
    text = re.sub("くょ", " ky o", text)
    text = re.sub("けぇ", " k e:", text)
    text = re.sub("けえ", " k e:", text)
    text = re.sub("こお", " k o:", text)
    text = re.sub("こう", " k o:", text)
    text = re.sub("こぉ", " k o:", text)
    text = re.sub("がぁ", " g a:", text)
    text = re.sub("があ", " g a:", text)
    text = re.sub("ぎぃ", " g i:", text)
    text = re.sub("ぎい", " g i:", text)
    text = re.sub("ぐう", " g u:", text)
    text = re.sub("ぐぅ", " g u:", text)
    text = re.sub("ぐゃ", " gy a", text)
    text = re.sub("ぐゅ", " gy u", text)
    text = re.sub("ぐょ", " gy o", text)
    text = re.sub("げぇ", " g e:", text)
    text = re.sub("げえ", " g e:", text)
    text = re.sub("ごぉ", " g o:", text)
    text = re.sub("ごお", " g o:", text)
    text = re.sub("さぁ", " s a:", text)
    text = re.sub("さあ", " s a:", text)
    text = re.sub("しぃ", " sh i:", text)
    text = re.sub("しい", " sh i:", text)
    text = re.sub("すぅ", " s u:", text)
    text = re.sub("すう", " s u:", text)
    text = re.sub("すゃ", " sh a", text)
    text = re.sub("すゅ", " sh u", text)
    text = re.sub("すょ", " sh o", text)
    text = re.sub("せぇ", " s e:", text)
    text = re.sub("せえ", " s e:", text)
    text = re.sub("そぉ", " s o:", text)
    text = re.sub("そう", " s o:", text)
    text = re.sub("そお", " s o:", text)
    text = re.sub("ざあ", " z a:", text)
    text = re.sub("ざぁ", " z a:", text)
    text = re.sub("じい", " j i:", text)
    text = re.sub("じぃ", " j i:", text)
    text = re.sub("ずう", " z u:", text)
    text = re.sub("ずぅ", " z u:", text)
    text = re.sub("ずゃ", " zy a", text)
    text = re.sub("ずゅ", " zy u", text)
    text = re.sub("ずょ", " zy o", text)
    text = re.sub("ぜえ", " z e:", text)
    text = re.sub("ぜぇ", " z e:", text)
    text = re.sub("ぞお", " z o:", text)
    text = re.sub("ぞう", " z o:", text)
    text = re.sub("ぞぉ", " z o:", text)
    text = re.sub("たあ", " t a:", text)
    text = re.sub("たぁ", " t a:", text)
    text = re.sub("ちい", " ch i:", text)
    text = re.sub("ちぃ", " ch i:", text)
    text = re.sub("つぁ", " ts a", text)
    text = re.sub("つぃ", " ts i", text)
    text = re.sub("つう", " ts u:", text)
    text = re.sub("つぅ", " ts u:", text)
    text = re.sub("つゃ", " ch a", text)
    text = re.sub("つゅ", " ch u", text)
    text = re.sub("つょ", " ch o", text)
    text = re.sub("つぇ", " ts e", text)
    text = re.sub("つぉ", " ts o", text)
    text = re.sub("てぇ", " t e:", text)
    text = re.sub("とぉ", " t o:", text)
    text = re.sub("とお", " t o:", text)
    text = re.sub("とう", " t o:", text)
    text = re.sub("だぁ", " d a:", text)
    text = re.sub("だあ", " d a:", text)
    text = re.sub("ぢぃ", " j i:", text)
    text = re.sub("ぢい", " j i:", text)
    text = re.sub("づぅ", " d u:", text)
    text = re.sub("づう", " d u:", text)
    text = re.sub("づゃ", " zy a", text)
    text = re.sub("づゅ", " zy u", text)
    text = re.sub("づょ", " zy o", text)
    text = re.sub("でぇ", " d e:", text)
    text = re.sub("でえ", " d e:", text)
    text = re.sub("どぉ", " d o:", text)
    text = re.sub("どお", " d o:", text)
    text = re.sub("どう", " d o:", text)
    text = re.sub("なぁ", " n a:", text)
    text = re.sub("なあ", " n a:", text)
    text = re.sub("にぃ", " n i:", text)
    text = re.sub("にい", " n i:", text)
    text = re.sub("ぬぅ", " n u:", text)
    text = re.sub("ぬう", " n u:", text)
    text = re.sub("ぬゃ", " ny a", text)
    text = re.sub("ぬゅ", " ny u", text)
    text = re.sub("ぬょ", " ny o", text)
    text = re.sub("ねぇ", " n e:", text)
    text = re.sub("ねえ", " n e:", text)
    text = re.sub("のぉ", " n o:", text)
    text = re.sub("のお", " n o:", text)
    text = re.sub("のう", " n o:", text)
    text = re.sub("はぁ", " h a:", text)
    text = re.sub("はあ", " h a:", text)
    text = re.sub("ひぃ", " h i:", text)
    text = re.sub("ひい", " h i:", text)
    text = re.sub("ふぅ", " f u:", text)
    text = re.sub("ふう", " f u:", text)
    text = re.sub("ふゃ", " hy a", text)
    text = re.sub("ふゅ", " hy u", text)
    text = re.sub("ふょ", " hy o", text)
    text = re.sub("へぇ", " h e:", text)
    text = re.sub("へえ", " h e:", text)
    text = re.sub("ほぉ", " h o:", text)
    text = re.sub("ほお", " h o:", text)
    text = re.sub("ほう", " h o:", text)
    text = re.sub("ばぁ", " b a:", text)
    text = re.sub("ばあ", " b a:", text)
    text = re.sub("びぃ", " b i:", text)
    text = re.sub("びい", " b i:", text)
    text = re.sub("ぶぅ", " b u:", text)
    text = re.sub("ぶう", " b u:", text)
    text = re.sub("ふゃ", " hy a", text)
    text = re.sub("ぶゅ", " by u", text)
    text = re.sub("ふょ", " hy o", text)
    text = re.sub("べぇ", " b e:", text)
    text = re.sub("べえ", " b e:", text)
    text = re.sub("ぼぉ", " b o:", text)
    text = re.sub("ぼお", " b o:", text)
    text = re.sub("ぼう", " b o:", text)
    text = re.sub("ぱぁ", " p a:", text)
    text = re.sub("ぱあ", " p a:", text)
    text = re.sub("ぴぃ", " p i:", text)
    text = re.sub("ぴい", " p i:", text)
    text = re.sub("ぷぅ", " p u:", text)
    text = re.sub("ぷう", " p u:", text)
    text = re.sub("ぷゃ", " py a", text)
    text = re.sub("ぷゅ", " py u", text)
    text = re.sub("ぷょ", " py o", text)
    text = re.sub("ぺぇ", " p e:", text)
    text = re.sub("ぺえ", " p e:", text)
    text = re.sub("ぽぉ", " p o:", text)
    text = re.sub("ぽお", " p o:", text)
    text = re.sub("ぽう", " p o:", text)
    text = re.sub("まぁ", " m a:", text)
    text = re.sub("まあ", " m a:", text)
    text = re.sub("みぃ", " m i:", text)
    text = re.sub("みい", " m i:", text)
    text = re.sub("むぅ", " m u:", text)
    text = re.sub("むう", " m u:", text)
    text = re.sub("むゃ", " my a", text)
    text = re.sub("むゅ", " my u", text)
    text = re.sub("むょ", " my o", text)
    text = re.sub("めえ", " m e:", text)
    text = re.sub("もお", " m o:", text)
    text = re.sub("やあ", " y a:", text)
    text = re.sub("ゆう", " y u:", text)
    text = re.sub("ゆゃ", " y a:", text)
    text = re.sub("ゆゅ", " y u:", text)
    text = re.sub("ゆょ", " y o:", text)
    text = re.sub("よぉ", " y o:", text)
    text = re.sub("よお", " y o:", text)
    text = re.sub("よう", " y o:", text)
    text = re.sub("らぁ", " r a:", text)
    text = re.sub("らあ", " r a:", text)
    text = re.sub("りぃ", " r i:", text)
    text = re.sub("りい", " r i:", text)
    text = re.sub("るぅ", " r u:", text)
    text = re.sub("るう", " r u:", text)
    text = re.sub("るゃ", " ry a", text)
    text = re.sub("るゅ", " ry u", text)
    text = re.sub("るょ", " ry o", text)
    text = re.sub("れぇ", " r e:", text)
    text = re.sub("れえ", " r e:", text)
    text = re.sub("ろぉ", " r o:", text)
    text = re.sub("ろお", " r o:", text)
    text = re.sub("ろう", " r o:", text)
    text = re.sub("わぁ", " w a:", text)
    text = re.sub("わあ", " w a:", text)
    text = re.sub("をぉ", " o:", text)
    text = re.sub("をお", " o:", text)
    text = re.sub("う゛", " b u", text)
    text = re.sub("でぃ", " d i", text)
    text = re.sub("でぇ", " d e:", text)
    text = re.sub("でえ", " d e:", text)
    text = re.sub("でゃ", " dy a", text)
    text = re.sub("でゅ", " dy u", text)
    text = re.sub("でょ", " dy o", text)
    text = re.sub("てぃ", " t i", text)
    text = re.sub("てぇ", " t e:", text)
    text = re.sub("てえ", " t e:", text)
    text = re.sub("てゃ", " ty a", text)
    text = re.sub("てゅ", " ty u", text)
    text = re.sub("てょ", " ty o", text)
    text = re.sub("すぃ", " s i", text)
    text = re.sub("ずぁ", " z u a", text)
    text = re.sub("ずぃ", " z i", text)
    text = re.sub("ずぅ", " z u", text)
    text = re.sub("ずゃ", " zy a", text)
    text = re.sub("ずゅ", " zy u", text)
    text = re.sub("ずょ", " zy o", text)
    text = re.sub("ずぇ", " z e", text)
    text = re.sub("ずぉ", " z o", text)
    text = re.sub("きゃ", " ky a", text)
    text = re.sub("きゅ", " ky u", text)
    text = re.sub("きょ", " ky o", text)
    text = re.sub("しゃ", " sh a", text)
    text = re.sub("しゅ", " sh u", text)
    text = re.sub("しぇ", " sh e", text)
    text = re.sub("しょ", " sh o", text)
    text = re.sub("ちゃ", " ch a", text)
    text = re.sub("ちゅ", " ch u", text)
    text = re.sub("ちぇ", " ch e", text)
    text = re.sub("ちょ", " ch o", text)
    text = re.sub("とぅ", " t u", text)
    text = re.sub("とゃ", " ty a", text)
    text = re.sub("とゅ", " ty u", text)
    text = re.sub("とょ", " ty o", text)
    text = re.sub("どぁ", " d o a", text)
    text = re.sub("どぅ", " d u", text)
    text = re.sub("どゃ", " dy a", text)
    text = re.sub("どゅ", " dy u", text)
    text = re.sub("どょ", " dy o", text)
    text = re.sub("どぉ", " d o:", text)
    text = re.sub("どお", " d o:", text)
    text = re.sub("どう", " d o:", text)
    text = re.sub("にゃ", " ny a", text)
    text = re.sub("にゅ", " ny u", text)
    text = re.sub("にょ", " ny o", text)
    text = re.sub("ひゃ", " hy a", text)
    text = re.sub("ひゅ", " hy u", text)
    text = re.sub("ひょ", " hy o", text)
    text = re.sub("みゃ", " my a", text)
    text = re.sub("みゅ", " my u", text)
    text = re.sub("みょ", " my o", text)
    text = re.sub("りゃ", " ry a", text)
    text = re.sub("りゅ", " ry u", text)
    text = re.sub("りょ", " ry o", text)
    text = re.sub("ぎゃ", " gy a", text)
    text = re.sub("ぎゅ", " gy u", text)
    text = re.sub("ぎょ", " gy o", text)
    text = re.sub("ぢぇ", " j e", text)
    text = re.sub("ぢゃ", " j a", text)
    text = re.sub("ぢゅ", " j u", text)
    text = re.sub("ぢょ", " j o", text)
    text = re.sub("じぇ", " j e", text)
    text = re.sub("じゃ", " j a", text)
    text = re.sub("じゅ", " j u", text)
    text = re.sub("じょ", " j o", text)
    text = re.sub("びゃ", " by a", text)
    text = re.sub("びゅ", " by u", text)
    text = re.sub("びょ", " by o", text)
    text = re.sub("ぴゃ", " py a", text)
    text = re.sub("ぴゅ", " py u", text)
    text = re.sub("ぴょ", " py o", text)
    text = re.sub("うぁ", " u a", text)
    text = re.sub("うぃ", " w i", text)
    text = re.sub("うぇ", " w e", text)
    text = re.sub("うぉ", " w o", text)
    text = re.sub("ふぁ", " f a", text)
    text = re.sub("ふぃ", " f i", text)
    text = re.sub("ふぅ", " f u", text)
    text = re.sub("ふゃ", " hy a", text)
    text = re.sub("ふゅ", " hy u", text)
    text = re.sub("ふょ", " hy o", text)
    text = re.sub("ふぇ", " f e", text)
    text = re.sub("ふぉ", " f o", text)
    # 1音からなる変換規則
    text = re.sub("あ", " a", text)
    text = re.sub("い", " i", text)
    text = re.sub("う", " u", text)
    text = re.sub("え", " e", text)
    text = re.sub("お", " o", text)
    text = re.sub("か", " k a", text)
    text = re.sub("き", " k i", text)
    text = re.sub("く", " k u", text)
    text = re.sub("け", " k e", text)
    text = re.sub("こ", " k o", text)
    text = re.sub("さ", " s a", text)
    text = re.sub("し", " sh i", text)
    text = re.sub("す", " s u", text)
    text = re.sub("せ", " s e", text)
    text = re.sub("そ", " s o", text)
    text = re.sub("た", " t a", text)
    text = re.sub("ち", " ch i", text)
    text = re.sub("つ", " ts u", text)
    text = re.sub("て", " t e", text)
    text = re.sub("と", " t o", text)
    text = re.sub("な", " n a", text)
    text = re.sub("に", " n i", text)
    text = re.sub("ぬ", " n u", text)
    text = re.sub("ね", " n e", text)
    text = re.sub("の", " n o", text)
    text = re.sub("は", " h a", text)
    text = re.sub("ひ", " h i", text)
    text = re.sub("ふ", " f u", text)
    text = re.sub("へ", " h e", text)
    text = re.sub("ほ", " h o", text)
    text = re.sub("ま", " m a", text)
    text = re.sub("み", " m i", text)
    text = re.sub("む", " m u", text)
    text = re.sub("め", " m e", text)
    text = re.sub("も", " m o", text)
    text = re.sub("ら", " r a", text)
    text = re.sub("り", " r i", text)
    text = re.sub("る", " r u", text)
    text = re.sub("れ", " r e", text)
    text = re.sub("ろ", " r o", text)
    text = re.sub("が", " g a", text)
    text = re.sub("ぎ", " g i", text)
    text = re.sub("ぐ", " g u", text)
    text = re.sub("げ", " g e", text)
    text = re.sub("ご", " g o", text)
    text = re.sub("ざ", " z a", text)
    text = re.sub("じ", " j i", text)
    text = re.sub("ず", " z u", text)
    text = re.sub("ぜ", " z e", text)
    text = re.sub("ぞ", " z o", text)
    text = re.sub("だ", " d a", text)
    text = re.sub("ぢ", " j i", text)
    text = re.sub("づ", " z u", text)
    text = re.sub("で", " d e", text)
    text = re.sub("ど", " d o", text)
    text = re.sub("ば", " b a", text)
    text = re.sub("び", " b i", text)
    text = re.sub("ぶ", " b u", text)
    text = re.sub("べ", " b e", text)
    text = re.sub("ぼ", " b o", text)
    text = re.sub("ぱ", " p a", text)
    text = re.sub("ぴ", " p i", text)
    text = re.sub("ぷ", " p u", text)
    text = re.sub("ぺ", " p e", text)
    text = re.sub("ぽ", " p o", text)
    text = re.sub("や", " y a", text)
    text = re.sub("ゆ", " y u", text)
    text = re.sub("よ", " y o", text)
    text = re.sub("わ", " w a", text)
    text = re.sub("ゐ", " i", text)
    text = re.sub("ゑ", " e", text)
    text = re.sub("ん", " N", text)
    text = re.sub("っ", " q", text)
    text = re.sub("ー", ":", text)
    # ここまでに処理されてない ぁぃぅぇぉ はそのまま大文字扱い
    text = re.sub("ぁ", " a", text)
    text = re.sub("ぃ", " i", text)
    text = re.sub("ぅ", " u", text)
    text = re.sub("ぇ", " e", text)
    text = re.sub("ぉ", " o", text)
    text = re.sub("ゎ", " w a", text)
    text = re.sub("ぉ", " o", text)
    # その他特別なルール
    text = re.sub("を", " o", text)
    text = re.sub("/", "", text)
    text = re.sub("-", "", text)
    text = re.sub("_", "", text)
    text = re.sub(":+", ":", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


if __name__ == "__main__":
    from argparse import ArgumentParser
    from json import dumps
    parser = ArgumentParser(description='音声ファイルに対し自動アラインメントを行います')
    parser.add_argument('-i', '--input', help='解析対象の wav ファイル')
    parser.add_argument('-o', '--output', help='認識結果を csv ファイルにして掃き出す')
    parser.add_argument('-t', '--text', help='音声ファイルの内容')
    parser.add_argument(
        '--voca', help='セグメント表記を csj にしない', action='store_true'
    )
    parser.add_argument('--test', help='doctest を実行', action='store_true')

    args = parser.parse_args()
    if args.test:
        import doctest
        doctest.testmod(verbose=True)
    else:
        julius = Julius(args.input, args.text)
        if args.voca:
            julius.run_segmentation(csj=False)
        julius.run_segmentation()
        if args.output:
            julius.to_csv(args.output)
        else:
            print(dumps(julius.result, indent=4, ensure_ascii=False))
