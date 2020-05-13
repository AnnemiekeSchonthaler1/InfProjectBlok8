import base64
from io import BytesIO

import numpy as np
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import csv

def Graph(dictionary):
    recipe = []
    fig, ax = plt.subplots(figsize=(6, 3), subplot_kw=dict(aspect="equal"))

    for k,v in dictionary.items():
        value = "{}: {}".format(k,v)
        recipe.append(value)

    data = list(dictionary.values())

    wedges, texts = ax.pie(data, wedgeprops=dict(width=0.5), startangle=-40)

    bbox_props = dict(boxstyle="square,pad=0.3", fc="w", ec="k", lw=0.72)
    kw = dict(arrowprops=dict(arrowstyle="-"),
              bbox=bbox_props, zorder=0, va="center")

    for i, p in enumerate(wedges):
        ang = (p.theta2 - p.theta1)/2. + p.theta1
        y = np.sin(np.deg2rad(ang))
        x = np.cos(np.deg2rad(ang))
        horizontalalignment = {-1: "right", 1: "left"}[int(np.sign(x))]
        connectionstyle = "angle,angleA=0,angleB={}".format(ang)
        kw["arrowprops"].update({"connectionstyle": connectionstyle})
        ax.annotate(recipe[i], xy=(x, y), xytext=(1.35*np.sign(x), 1.4*y),
                    horizontalalignment=horizontalalignment, **kw)
    ax.set_title("Amount of Articles found per Gene")
    return plt



def save_to_url(plt):
    img = BytesIO()
    plt.savefig(img, format='png')
    plt.close()
    img.seek(0)
    plot_url = base64.b64encode(img.getvalue()).decode('utf8')
    return plot_url

def wordcloud(dictionary):
    # {pubmedid:{type:[naam], type:[naam]}
    text = ""
    for dic in dictionary.values():
        for naam in dic:
            text = text + " " + naam

    print(text)
    wordcloud = WordCloud(background_color="white", width=480, height=480, colormap="plasma").generate(text)

    # plot the WordCloud image
    plt.figure()
    plt.imshow(wordcloud, interpolation="bilinear")
    plt.axis("off")
    plt.margins(x=0, y=0)
    URL = save_to_url(plt)
    return URL
