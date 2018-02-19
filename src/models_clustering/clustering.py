import numpy as np
import pandas as pd
import sys, os

dist_no = sys.argv[1]
dist = "./data/processed/csj/"+dist_no
ext = "./data/external/"
answer_path = ext+"CJLC-0.1/"+dist_no+'.txt'

# ### answerにfreqそれぞれの単語が存在するかのフラグを作る

answer = ""
with open(answer_path) as fh:
    answer = fh.read()

freq = pd.read_csv(dist+'/freqency.csv',header=None)

# general wordsを除外
gw = pd.read_pickle(ext+"/general_words_300.pd")
freq = freq[~freq[0].isin(gw[0])]

freq_flag = freq.apply(lambda word: answer.find(word.values[0]) is not -1, axis=1)

# ### freqに特徴量とベクトルを追加する
freq.columns = ['単語','出現回数','平均信頼度']
freq['正誤'] = freq_flag
freq['A'] = freq['出現回数'] * freq['平均信頼度']
freq['logA'] = freq['A'].apply(lambda x: np.log(x))
freq['sqrtA'] = freq['A'].apply(lambda x: np.sqrt(x))

w2v_all = [
    pd.read_pickle(ext+'/w2v50.pd'),
    pd.read_pickle(ext+'/w2v200.pd')
]

w2v_all = [w[~w.index.isin(gw[0])] for w in w2v_all]

w2v_freq = [w[w.index.isin(freq['単語'])] for w in w2v_all]


import numpy as np
from scipy import stats
import matplotlib.pyplot as plt
import matplotlib.font_manager

from sklearn import svm
from sklearn.covariance import EllipticEnvelope
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor

import pandas as pd
import csv

# Seed
rng = np.random.RandomState(42)

# データ
n_samples = len(freq)


# ## パラメータ
# - One-Class SVM
#     - nu
#         - 0.001, 0.05, 0.1, 0.25
# - Isolation Forest
#     - outliners_fraction
#         - 0.05,0.2,0.5
# - LOF
#     - outliners_fraction
#         - 0.05,0.2,0.5
#     - n_neighbors
#         - 5, 35, 70
# - Word2Vec Model
#     - 50 or 200
# - duplicate(n)
#     - そのまま (n)
#     - 頻度による変化 n' = (n*round(A))
#     - log(n')
#     - sqrt(n')
# - 出現回数10?回以上
# 
# = ( 4 + 3 + 3\*3 ) \* 2 \* 4 \* 2  
# = 256 pattern

from itertools import product

params = [
    [0, 1],                         # わからない
    ['n', 'A', 'logA', 'sqrtA'],    # わからない
    [0, 5, 10],                        # 5-10あたりがいい？
    ['SVM', 'IF', 'LOF'],           # SVM or LOF?
]
model_params = {
    'SVM': {'nu':[0.001, 0.05, 0.1, 0.25]}, # 0.1, 0.25が良い
    'IF' : {'of':[0.05,0.2,0.5]},           #
    'LOF': {'of':[0.05,0.2,0.5],            # 0.5   0.5
            'nn':[5,35,70]}                 # 5     35
}

print("DISP START")

param_list = [
    (1,'A',10,'SVM'),
    (1,'A',10,'LOF'),
    (1,'logA',10,'SVM'),
    (1,'n',10,'SVM'),
    (1,'A',5,'IF'),
    (0,'A',10,'LOF'),
    (0,'logA',10,'SVM'),
    (0,'sqrtA',10,'SVM'),
    (0,'n',10,'SVM'),
    (0,'n',10,'LOF'),
    (0,'A',0,'IF'),
    (0,'A',10,'SVM'),
#    (1,'A',10,'SVM'),
#    (1,'n',5,'SVM'),
#    (1,'A',5,'SVM'),
#    (1,'logA',5,'SVM'),
#    (1,'n',10,'SVM'),
#    (1,'A',10,'LOF'),
#    (1,'n',10,'IF'),
]
model_param_list = {
    'IF' : [[0.05,0.2]],
    'SVM': [[0.05,0.1,0.25]],
    'LOF': [[0.05,0.5],[5]],
}

from matplotlib import pyplot as plt


cnt = 0
for param in product(*params):
    if param not in param_list:
        continue
    w2v_f = w2v_freq[param[0]]
    w2v_a = w2v_all[param[0]]
    w2v_param = param[0]
    a_type = param[1]
    count_threshold = param[2]
    clustering_model_type = param[3]
    for model_param in product(*model_params[clustering_model_type].values()):
        if model_param[0] not in model_param_list[clustering_model_type][0]:
            continue
        if clustering_model_type == 'LOF' and model_param[1] not in model_param_list[clustering_model_type][1]:
            continue
        #X = w2v[w2v.index.isin(freq[freq['A'] > count_threshold]['単語'])]
        #Z = w2v[w2v.index.isin(freq[(freq['A'] > 10) | (freq['正誤'] == False)]['単語'])]
        X = w2v_f[w2v_f.index.isin(freq[freq['A']     > count_threshold  ]['単語'])]
        #V = w2v[w2v.index.isin(freq[freq['A']     > 10             ]['単語'])]
        #F = w2v[w2v.index.isin(freq[freq['正誤'] == False           ]['単語'])]
        #msk = np.random.rand(len(V)) < 0.6
        #trainV = V[msk]
        #testV = V[~msk]
        #X = C[~C.index.isin(trainV.index)] #X is train
        #Z = testV.append(F) #Z is test

        Z = w2v_a


        if a_type != 'n':
            X_cnt = [ int(np.round(freq[freq['単語'] == word][a_type])) for word in X.index]
            buf = []
            for (i,c) in zip(range(len(X)),X_cnt):
                for ci in range(c):
                    buf.append(X.ix[[i],:].values[0])
            X = np.array(buf)

        if clustering_model_type == 'SVM':
            model = svm.OneClassSVM(nu=model_param[0], kernel="rbf", gamma="auto")
            model.fit(X)
            model.predict(X)
            score = model.decision_function(Z)
            score = [s[0] for s in score]
        elif clustering_model_type == 'IF':
            model = IsolationForest(max_samples=n_samples, contamination=model_param[0], random_state=rng)
            model.fit(X)
            score = model.decision_function(Z)
        elif clustering_model_type == 'LOF':
            model = LocalOutlierFactor(n_neighbors=model_param[1], contamination=model_param[0])
            model.fit_predict(X)
            score = model._decision_function(Z)

        # Save Z
        Z_with_word = pd.DataFrame(list(zip(Z.index,score)))
        Z_with_word = Z_with_word.sort_values(by=1, ascending=False)
        name = (dist+'/clustering'
            +'-'+('50' if w2v_param == 0 else '200')
            +'-'+str(count_threshold)
            +'-'+a_type
            +'-'+clustering_model_type
            +'-'+str(model_param[0])
            +str('' if len(model_param) == 1 else '-'+str(model_param[1]))
        )
        print('save file. name is "'+name+'"')
        Z_with_word.to_csv(name,header=None,index=False)

"""
cnt = 0
scnt = 1
fig = plt.figure()
for param in product(*params):
    if scnt == 17:
        fig.canvas.set_window_title(
            'cnt='+str(cnt)
            #+' model='+clustering_model_type
            +' w2v='+('50' if w2v_param == 0 else '200')
            +' type='+a_type
            +' threshold='+str(count_threshold)
            #+' p1='+str(model_param[0])
            #+' p2='+str("none" if len(model_param) == 1 else model_param[1])
        )
        figManager = plt.get_current_fig_manager()
        figManager.window.showMaximized()
        plt.show()
        scnt = 1
        fig = plt.figure()
        cnt += 1
    w2v = w2v_freq[param[0]]
    w2v_param = param[0]
    a_type = param[1]
    count_threshold = param[2]
    clustering_model_type = param[3]
    for model_param in product(*model_params[clustering_model_type].values()):
        #X = w2v[w2v.index.isin(freq[freq['A'] > count_threshold]['単語'])]
        #Z = w2v[w2v.index.isin(freq[(freq['A'] > 10) | (freq['正誤'] == False)]['単語'])]
        C = w2v[w2v.index.isin(freq[freq['A']     > count_threshold  ]['単語'])]
        V = w2v[w2v.index.isin(freq[freq['A']     > 10             ]['単語'])]
        F = w2v[w2v.index.isin(freq[freq['正誤'] == False           ]['単語'])]
        msk = np.random.rand(len(V)) < 0.6
        trainV = V[msk]
        testV = V[~msk]
        X = C[~C.index.isin(trainV.index)] #X is train
        Z = testV.append(F) #Z is test


        if a_type != 'n':
            X_cnt = [ int(np.round(freq[freq['単語'] == word][a_type])) for word in X.index]
            buf = []
            for (i,c) in zip(range(len(X)),X_cnt):
                for ci in range(c):
                    buf.append(X.ix[[i],:].values[0])
            X = np.array(buf)

        if clustering_model_type == 'SVM':
            model = svm.OneClassSVM(nu=model_param[0], kernel="rbf", gamma="auto")
            model.fit(X)
            score = model.decision_function(Z)
            score = [s[0] for s in score]
        elif clustering_model_type == 'IF':
            model = IsolationForest(max_samples=n_samples, contamination=model_param[0], random_state=rng)
            model.fit(X)
            score = model.decision_function(Z)
        elif clustering_model_type == 'LOF':
            model = LocalOutlierFactor(n_neighbors=model_param[1], contamination=model_param[0])
            model.fit_predict(X)
            score = model._decision_function(Z)

        ax = fig.add_subplot(4,4,scnt)

        yg = np.array([freq[freq['単語'] == word]['正誤'].values[0] for word in Z.index]) # z flag
        xg = np.array(score) # z
        ax.scatter(xg,yg)
        ax.grid(True)
        ax.title.set_text(
            'cnt='+str(cnt)
            +' model='+clustering_model_type
            +' p1='+str(model_param[0])
            +' p2='+str("none" if len(model_param) == 1 else model_param[1])
        )
        ax.axis([np.partition(xg, 2)[2],xg.max(), -0.2, 1.2])
        scnt += 1

"""