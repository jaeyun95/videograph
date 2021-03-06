# !/usr/bin/env python
# -*- coding: UTF-8 -*-

########################################################################
# GNU General Public License v3.0
# GNU GPLv3
# Copyright (c) 2019, Noureldien Hussein
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
########################################################################

"""
Analysis for Breakfast dataset.
"""

import os
import cv2
import numpy as np
import matplotlib
import seaborn as sns
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib import lines as m_lines
from scipy.spatial import distance
from sklearn.metrics import confusion_matrix
from MulticoreTSNE import MulticoreTSNE

import tensorflow as tf
import keras.backend as K

from nets.keras_layers import ReshapeLayer, TransposeLayer, MaxLayer, MeanLayer, DepthwiseConv1DLayer, ExpandDimsLayer

from datasets import ds_breakfast
from core import utils, keras_utils, plot_utils
from core import const as c
from core.utils import Path as Pth

# region Qualitative

def _01_get_nodes_over_epochs():
    """
    Get centroids of the model.
    :return:
    """

    n_centroids = 128
    n_epochs = 100
    model_name = 'classifier_19.02.21-01:00:30'
    model_root_path = Pth('Breakfast/models/%s', (model_name,))
    centroids_path = Pth('Breakfast/features_centroids/features_random_%d_centroids.pkl', (n_centroids,))
    nodes_root_path = Pth('Breakfast/qualitative_results/node_embedding_%s' % (model_name,))

    v_input_nodes = utils.pkl_load(centroids_path)

    model = None
    t_input_nodes = None
    t_node_embedding = None
    keras_session = K.get_session()

    for idx_epoch in range(n_epochs):

        utils.print_counter(idx_epoch, n_epochs)

        epoch_num = idx_epoch + 1
        weight_path = '%s/%03d.pkl' % (model_root_path, epoch_num)

        if epoch_num == 1:
            model = __load_model(model_name, epoch_num)
            t_input_nodes = model.get_layer('input_n').input
            t_node_embedding = model.get_layer('node_embedding').output
        else:
            model.load_weights(weight_path)

        v_node_embedding, = keras_session.run([t_node_embedding], {t_input_nodes: v_input_nodes})  # (1, 128, 1024)
        v_node_embedding = np.squeeze(v_node_embedding, axis=0)  # (1, 128, 1024)
        path = '%s/%02d.pkl' % (nodes_root_path, epoch_num)
        utils.pkl_dump(v_node_embedding, path)

    pass

def _02_plot_nodes_over_epochs():
    sns.set_style('whitegrid')
    sns.set(style='darkgrid')

    n_epochs = 50
    node_dim = 1024
    n_centroids = 128

    # for plotting
    is_async_tsne = True
    window_size = 15
    n_max_centroids = 40

    model_name = 'classifier_19.02.21-01:00:30'
    nodes_root_path = Pth('Breakfast/qualitative_results/node_embedding_%s' % (model_name,))

    # load nodes from files
    nodes = []
    nodes_file_pathes = utils.file_pathes(nodes_root_path, is_nat_sort=True)
    for i in range(n_epochs):
        n = utils.pkl_load(nodes_file_pathes[i])
        nodes.append(n)
    nodes = np.array(nodes)  # (50, 128, 1024)
    nodes = nodes[:, 0:n_max_centroids]  # (50, 100, 1024)
    n_centroids = n_max_centroids
    print nodes.shape

    # embed the nodes
    nodes_1 = nodes[:window_size]
    nodes_2 = nodes[-window_size:]
    print nodes_1.shape
    print nodes_2.shape
    nodes_1 = np.reshape(nodes_1, (-1, node_dim))
    nodes_2 = np.reshape(nodes_2, (-1, node_dim))
    print nodes_1.shape
    print nodes_2.shape
    nodes_1 = __async_tsne_embedding(nodes_1) if is_async_tsne else utils.learn_manifold(c.MANIFOLD_TYPES[0], nodes_1)
    nodes_2 = __async_tsne_embedding(nodes_2) if is_async_tsne else utils.learn_manifold(c.MANIFOLD_TYPES[0], nodes_2)
    nodes_1 = np.reshape(nodes_1, (window_size, n_centroids, 2))  # (50, 100, 1024)
    nodes_2 = np.reshape(nodes_2, (window_size, n_centroids, 2))  # (50, 100, 1024)
    print nodes_1.shape
    print nodes_2.shape

    # colors = plot_utils.tableau_category20()
    colors = plot_utils.colors_256()
    colors_1 = colors[:n_centroids]
    colors_2 = colors[n_centroids + 1: n_centroids + n_centroids + 1]

    __plot_centroids(nodes_1, window_size, n_centroids, colors_1, 1)
    __plot_centroids(nodes_2, window_size, n_centroids, colors_2, 2)

def _03_mean_std_of_nodes():
    sns.set_style('whitegrid')
    sns.set(style='darkgrid')
    sns.set(style='darkgrid')  # white, dark, whitegrid, darkgrid, ticks

    n_epochs = 100
    node_dim = 1024
    n_centroids = 128

    model_name = 'classifier_19.02.21-01:00:30'
    nodes_root_path = Pth('Breakfast/qualitative_results/node_embedding_%s' % (model_name,))

    # load nodes from files
    nodes = []
    nodes_file_pathes = utils.file_pathes(nodes_root_path, is_nat_sort=True)
    for i in range(n_epochs):
        n = utils.pkl_load(nodes_file_pathes[i])
        nodes.append(n)
    nodes = np.array(nodes)  # (50, 128, 1024)

    distances = []
    for i in range(n_epochs):
        n = nodes[i]
        n = utils.normalize_l1(n)
        d = distance.cdist(n, n, metric='euclidean')
        d = np.mean(d)
        distances.append(d)

    distances = np.array(distances)

    fig, ax = plt.subplots(nrows=1, ncols=1, num=1, figsize=(4, 2))
    colors = plot_utils.tableau_category10()
    ax.set_title('')

    y = distances
    x = np.arange(1, n_epochs + 1)

    fit_fn = np.poly1d(np.polyfit(x, y, 4))
    y_fit = fit_fn(x)
    sigma = 0.005

    plt.fill_between(x, y_fit + sigma, y_fit - sigma, facecolor=colors[0], alpha=0.25)
    ax.plot(x, y, '.', c=colors[0], markersize=9, alpha=1.0)
    ax.plot(x, y_fit, color='black', lw=1)

    plt.tight_layout()
    plt.subplots_adjust(left=0.2, right=0.9, top=0.9, bottom=0.3)
    plt.grid('off')
    plt.xlabel('Epoch Number')
    plt.ylabel('Distance')
    plt.show()

def _04_get_activation_values():
    # load data
    n_timesteps = 64
    n_centroids = 128

    model_name = 'classifier_19.02.21-01:00:30'
    features_path = Pth('Breakfast/features/features_i3d_mixed_5c_%d_frames.h5', (n_timesteps * 8,))
    centroids_path = Pth('Breakfast/features_centroids/features_random_%d_centroids.pkl', (n_centroids,))
    attention_values_path = Pth('Breakfast/qualitative_results/node_attention_%s.pkl', (model_name,))

    v_input_n = utils.pkl_load(centroids_path)
    (x_tr, x_te) = utils.h5_load_multi(features_path, ['x_tr', 'x_te'])

    epoch_num = 133
    model = __load_model(model_name, epoch_num)

    t_input_n = model.get_layer('input_n').input
    t_input_x = model.get_layer('input_x').input
    t_node_attention = model.get_layer('node_attention').output  # # (None, 7, 7, 64, 100)
    keras_session = K.get_session()

    batch_size = 40
    att_tr = __get_tensor_values(batch_size, keras_session, t_node_attention, t_input_n, t_input_x, v_input_n, x_tr)  # (None, 1, 1, 64, 128)
    att_te = __get_tensor_values(batch_size, keras_session, t_node_attention, t_input_n, t_input_x, v_input_n, x_te)  # (None, 1, 1, 64, 128)

    att_tr = np.squeeze(att_tr, axis=1)  # (None, 1, 64, 128)
    att_tr = np.squeeze(att_tr, axis=1)  # (None, 64, 128)
    att_te = np.squeeze(att_te, axis=1)  # (None, 1, 64, 128)
    att_te = np.squeeze(att_te, axis=1)  # (None, 64, 128)

    print ('finally')
    print x_tr.shape
    print x_te.shape

    print att_tr.shape
    print att_te.shape

    utils.pkl_dump((att_tr, att_te), attention_values_path)

def _05_visualize_attention_values():
    # load data
    n_timesteps = 64
    n_centroids = 128

    model_name = 'classifier_19.02.21-01:00:30'
    features_path = Pth('Breakfast/features/features_i3d_mixed_5c_%d_frames.h5', (n_timesteps * 8,))
    gt_activities_path = Pth('Breakfast/annotation/gt_activities.pkl')
    frames_annot_path = Pth('Breakfast/annotation/annot_frames_i3d_%d.pkl', (512,))
    attention_values_path = Pth('Breakfast/qualitative_results/node_attention_%s.pkl', (model_name,))

    n_classes = ds_breakfast.N_CLASSES_ACTIVITIES
    frames_annot = utils.pkl_load(frames_annot_path)
    (video_ids_tr, y_tr), (video_ids_te, y_te) = utils.pkl_load(gt_activities_path)
    y_tr = utils.debinarize_label(y_tr)
    y_te = utils.debinarize_label(y_te)

    (att_tr, att_te) = utils.pkl_load(attention_values_path)  # (1357, 64, 128), (355, 64, 128)

    attentions_tr = np.array([np.average(att_tr[np.where(y_tr == idx_class)[0]], axis=(0, 1)) for idx_class in range(n_classes)])  # (10, 128)
    attentions_te = np.array([np.average(att_te[np.where(y_te == idx_class)[0]], axis=(0, 1)) for idx_class in range(n_classes)])  # (10, 128)

    # remove least attended centroids
    all_attn_vals = np.mean(attentions_tr, axis=1)

    _ = 10

    # plt.plot(np.transpose(attentions_te))
    # plt.show()

def _06_get_graph_edges():
    # load data
    n_timesteps = 64
    n_centroids = 128
    is_max_layer = True

    model_name = 'classifier_19.02.21-01:00:30'
    features_path = Pth('Breakfast/features/features_i3d_mixed_5c_%d_frames.h5', (n_timesteps * 8,))
    centroids_path = Pth('Breakfast/features_centroids/features_random_%d_centroids.pkl', (n_centroids,))

    if is_max_layer:
        edge_values_path = Pth('Breakfast/qualitative_results/graph_edges_max_%s.h5', (model_name,))
        edge_pooled_values_path = Pth('Breakfast/qualitative_results/graph_edges_max_reduced_%s.pkl', (model_name,))
        layer_name = 'pool_t_1'
        n_timesteps = 21
        n_nodes = 10
    else:
        edge_values_path = Pth('Breakfast/qualitative_results/graph_edges_relu_%s.h5', (model_name,))
        edge_pooled_values_path = Pth('Breakfast/qualitative_results/graph_edges_relu_reduced_%s.pkl', (model_name,))
        layer_name = 'leaky_re_lu_3'
        n_timesteps = 64
        n_nodes = 32

    v_input_n = utils.pkl_load(centroids_path)
    (x_tr, x_te) = utils.h5_load_multi(features_path, ['x_tr', 'x_te'])

    epoch_num = 133
    batch_size = 40
    model = __load_model(model_name, epoch_num)

    t_input_n = model.get_layer('input_n').input
    t_input_x = model.get_layer('input_x').input
    t_activations = model.get_layer(layer_name).output  # (None * 64, 32, 1, 1, 1024)
    keras_session = K.get_session()

    # 1357 train, 335 test
    vals_tr = __get_tensor_values(batch_size, keras_session, t_activations, t_input_n, t_input_x, v_input_n, x_tr)  # (None*64, 32, 1, 1, 1024)
    vals_te = __get_tensor_values(batch_size, keras_session, t_activations, t_input_n, t_input_x, v_input_n, x_te)  # (None*64, 32, 1, 1, 1024)

    vals_tr = np.squeeze(vals_tr, axis=2)
    vals_tr = np.squeeze(vals_tr, axis=2)

    vals_te = np.squeeze(vals_te, axis=2)
    vals_te = np.squeeze(vals_te, axis=2)

    n_tr = 1357
    n_te = 355
    if is_max_layer:
        vals_tr = np.reshape(vals_tr, (n_tr, n_nodes, n_timesteps, 1024))  # (None, timesteps, nodes, feat_size), (1357, 10, 21, 1024)
        vals_te = np.reshape(vals_te, (n_te, n_nodes, n_timesteps, 1024))  # (None, timesteps, nodes, feat_size), (355, 10, 21, 1024)
    else:
        vals_tr = np.reshape(vals_tr, (n_tr, n_timesteps, n_nodes, 1024))  # (None, timesteps, nodes, feat_size), (1357, 64, 32, 1024)
        vals_te = np.reshape(vals_te, (n_te, n_timesteps, n_nodes, 1024))  # (None, timesteps, nodes, feat_size), (355, 64, 32, 1024)

    print ('finally')
    print x_tr.shape
    print x_te.shape

    print vals_tr.shape
    print vals_te.shape

    utils.h5_dump_multi((vals_tr, vals_te), ['x_tr', 'x_te'], edge_values_path)

    vals_tr = np.mean(vals_tr, axis=3)
    vals_te = np.mean(vals_te, axis=3)
    utils.pkl_dump((vals_tr, vals_te), edge_pooled_values_path)

def _07_visualize_graph_edges():
    # load data
    n_timesteps = 64
    is_max_layer = True

    model_name = 'classifier_19.02.21-01:00:30'
    features_path = Pth('Breakfast/features/features_i3d_mixed_5c_%d_frames.h5', (n_timesteps * 8,))
    gt_activities_path = Pth('Breakfast/annotation/gt_activities.pkl')
    frames_annot_path = Pth('Breakfast/annotation/annot_frames_i3d_%d.pkl', (512,))
    class_names_path = Pth('Breakfast/annotation/activities_list.pkl')

    if is_max_layer:
        edge_values_path = Pth('Breakfast/qualitative_results/graph_edges_max_%s.h5', (model_name,))
        n_timesteps = 21
        n_nodes = 10
    else:
        edge_values_path = Pth('Breakfast/qualitative_results/graph_edges_relu_%s.h5', (model_name,))
        n_timesteps = 64
        n_nodes = 32

    n_classes = ds_breakfast.N_CLASSES_ACTIVITIES
    frames_annot = utils.pkl_load(frames_annot_path)
    class_names = utils.pkl_load(class_names_path)
    (video_ids_tr, y_tr), (video_ids_te, y_te) = utils.pkl_load(gt_activities_path)
    y_tr = utils.debinarize_label(y_tr)
    y_te = utils.debinarize_label(y_te)
    n_classes = ds_breakfast.N_CLASSES_ACTIVITIES

    if is_max_layer:
        # (1357, 10, 21)
        # (355, 10, 21)
        (x_tr, x_te,) = utils.h5_load_multi(edge_values_path, ['x_tr', 'x_te'])

        x_tr = np.transpose(x_tr, (0, 2, 1, 3))  # (1357, 21, 10, 1024)
        x_te = np.transpose(x_te, (0, 2, 1, 3))  # (355, 21, 10)
    else:
        # (1357, 64, 32, 1024)
        # (355, 64, 32, 1024)
        (x_tr, x_te) = utils.pkl_load(edge_values_path)

    x_original = x_tr
    y = y_tr

    assert n_timesteps == x_original.shape[1]
    assert n_nodes == x_original.shape[2]

    # pool over time
    x = np.mean(x_original, axis=1)  # (None, N, C)

    padding = 3
    node_ids = np.arange(n_nodes)

    x_sum_mean = np.mean(np.sum(x, axis=2), axis=0)
    min_node_value = min(x_sum_mean)
    max_node_value = max(x_sum_mean)

    def _scale_val(val):
        val = 1 / val
        val = pow(val, 1.2)
        return val

    # loop on classes of the dataset
    for idx_class in range(n_classes):

        class_num = idx_class + 1
        class_name = class_names[idx_class]
        idx_samples = np.where(y == idx_class)[0]
        x_class = x[idx_samples]  # (None, N, C)

        # pool over samples
        x_class = np.mean(x_class, axis=0)  # (N, C)
        graph = nx.Graph()

        node_values = np.sum(x_class, axis=1)

        # add the items as nodes to the graph
        for id in node_ids:
            if not graph.has_node(id):
                graph.add_node(id)

        max_edge_val = 0.0
        min_edge_val = 10000
        for idx_node in range(n_nodes):
            for idx_col in range(idx_node - padding, idx_node + padding + 1):
                for idx_row in range(idx_node - padding, idx_node + padding + 1):
                    if idx_col < 0 or idx_col >= n_nodes:
                        continue
                    if idx_row < 0 or idx_row >= n_nodes:
                        continue
                    if idx_row == idx_col:
                        continue
                    val = distance.euclidean(x_class[idx_row], x_class[idx_col])
                    val = _scale_val(val)
                    min_edge_val = min(min_edge_val, val)
                    max_edge_val = max(max_edge_val, val)

        for idx_node in range(n_nodes):
            for idx_col in range(idx_node - padding, idx_node + padding + 1):
                for idx_row in range(idx_node - padding, idx_node + padding + 1):

                    if idx_col < 0 or idx_col >= n_nodes:
                        continue
                    if idx_row < 0 or idx_row >= n_nodes:
                        continue
                    if idx_row == idx_col:
                        continue

                    # this value represents edges between nodes in local window of size 7
                    val = distance.euclidean(x_class[idx_row], x_class[idx_col])
                    val = _scale_val(val)
                    id_1 = idx_col
                    id_2 = idx_row

                    # add edge if not exist, else, get old duration and average it with current one
                    if not graph.has_edge(id_1, id_2):
                        graph.add_edge(id_1, id_2, vals=[val], val=val)
                    else:
                        vals = [val] + graph.get_edge_data(id_1, id_2)['vals']
                        val = np.average(vals)
                        graph[id_1][id_2]['vals'] = vals
                        graph[id_1][id_2]['val'] = val

        # now plot this graph
        g_edges = graph.edges
        g_nodes = graph.nodes

        # embed the graph
        # g_embedding = __async_tsne_embedding(x_class)
        # g_embedding = nx.random_layout(graph)
        # g_embedding = nx.spectral_layout(graph, weight='val') # spectral embedding with matrix laplacian
        # g_embedding = nx.kamada_kawai_layout(graph, weight='val', scale=10, dim=2)  # optimal distance between nodes
        g_embedding = nx.spring_layout(graph, weight='val', iterations=1000, scale=10, dim=2, seed=101)

        # plot graph
        __plot_embedded_graph(graph, g_embedding, g_edges, node_values, class_num, class_name, min_node_value, max_node_value, min_edge_val, max_edge_val, n_nodes)

def __plot_temporal_transitions(node_values, transitions, class_id, class_name, min_node_value, max_node_value, min_edge_value, max_edge_value, n_nodes):
    # plot graph
    colors = plot_utils.colors_256()
    colors = plot_utils.tableau_category10(True) / 255.0
    plt.figure(1, (5, 3.5))
    sns.set()

    min_line_width = 0.1
    max_line_width = 10

    min_marker_size = 5
    max_marker_size = 10

    min_opacity = 0.2
    max_opacity = 0.8

    color_threshold = 3 * 0.5
    x_min, x_max = 1000, -1000
    y_min, y_max = 1000, -1000

    node_ids = np.arange(n_nodes)
    node_ids = np.sort(node_ids)

    def __scale_line_width(val):
        scale_1 = float(max_line_width - min_line_width)
        scale_2 = float(max_edge_value - min_edge_value)
        x = (val - min_edge_value) * scale_1 / scale_2
        x = x + min_line_width
        return x

    def __scale_node_size(val):
        scale_1 = float(max_marker_size - min_marker_size)
        scale_2 = float(max_node_value - min_node_value)
        x = (val - min_node_value) * scale_1 / scale_2
        x = x + min_marker_size
        return x

    def __scale_opacity(val):
        scale_1 = float(max_opacity - min_opacity)
        scale_2 = float(max_edge_value - min_edge_value)
        x = (val - min_edge_value) * scale_1 / scale_2
        x = x + min_opacity
        return x

    # first, plot edges
    n_hops = len(transitions)
    for idx_hop, values in enumerate(transitions):

        for idx_t1 in range(n_nodes):
            for idx_t2 in range(idx_t1, n_nodes):
                x1, x2 = idx_hop + 1, idx_hop + 1
                y1 = idx_t1 + 1
                y2 = idx_t2 + 1
                x, y = (x1, x2), (y1, y2)
                edge_value = values[idx_t1, idx_t2]
                lw = __scale_line_width(edge_value)
                op = __scale_opacity(edge_value)
                plt.plot(x, y, lw=lw, color='gray', alpha=op)

    # second, plot nodes
    for idx_hop, values in enumerate(node_values):
        for idx_node, node_id in enumerate(node_ids):
            color = colors[idx_node]
            x = idx_hop + 1
            y = idx_node + 1
            node_value = values[idx_node]
            node_size = __scale_node_size(node_value)
            plt.plot(x, y, 'o', markersize=node_size, markeredgecolor='k', markerfacecolor=color)

        # also, plot text
        # plt.text(x, y, node_num, size=8, weight="bold", ha="center", va="center", color=text_color)

    alphabets = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']
    title = '%02d %s' % (class_id, class_name)
    title = '(%s) %s' % (alphabets[class_id - 1], class_name)
    plt.tight_layout()
    plt.subplots_adjust(left=0.0, right=1.0, top=1.0, bottom=0.0)
    # plt.tight_layout()
    plt.xticks(np.arange(1, n_hops + 1))
    plt.yticks(np.arange(1, n_nodes + 1))
    # plt.xlim([x_min, x_max])
    # plt.ylim([y_min, y_max])
    # plt.show()
    fig_num = class_id
    plt.savefig('/home/nour/Documents/Datasets/Breakfast/qualitative_results/breakfast_transitions/4-8-%s.png' % (fig_num))
    plt.savefig('/home/nour/Documents/Datasets/Breakfast/qualitative_results/breakfast_transitions/4-8-%s.pdf' % (fig_num))
    plt.clf()
    _ = 10

def __plot_embedded_graph(graph, g_embedding, g_edges, node_values, class_id, class_name, min_node_value, max_node_value, min_edge_value, max_edge_value, n_nodes):
    # plot graph
    colors = plot_utils.colors_256()
    colors = plot_utils.tableau_category10(True) / 255.0
    plt.figure(1, (5, 3.5))
    sns.set()

    min_line_width = 0.1
    max_line_width = 5

    min_marker_size = 10
    max_marker_size = 35

    min_opacity = 0.0
    max_opacity = 0.8

    color_threshold = 3 * 0.5
    x_min, x_max = 1000, -1000
    y_min, y_max = 1000, -1000

    node_ids = np.arange(n_nodes)
    node_ids = np.sort(node_ids)

    def __scale_line_width(val):
        scale_1 = float(max_line_width - min_line_width)
        scale_2 = float(max_edge_value - min_edge_value)
        x = (val - min_edge_value) * scale_1 / scale_2
        x = x + min_line_width
        return x

    def __scale_node_size(val):
        scale_1 = float(max_marker_size - min_marker_size)
        scale_2 = float(max_node_value - min_node_value)
        x = (val - min_node_value) * scale_1 / scale_2
        x = x + min_marker_size
        return x

    def __scale_opacity(val):
        scale_1 = float(max_opacity - min_opacity)
        scale_2 = float(max_edge_value - min_edge_value)
        x = (val - min_edge_value) * scale_1 / scale_2
        x = x + min_opacity
        return x

    # first, plot edges
    for idx_edge, edge in enumerate(g_edges):
        n1, n2 = edge
        (x1, y1), (x2, y2) = g_embedding[n1], g_embedding[n2]
        x, y = (x1, x2), (y1, y2)
        edge_value = graph[n1][n2]['val']
        lw = __scale_line_width(edge_value)
        op = __scale_opacity(edge_value)
        plt.plot(x, y, lw=lw, color='gray', alpha=op)

    # second, plot nodes
    legend_handles = []
    for idx_node, node_id in enumerate(node_ids):
        color = colors[idx_node]
        text_color = 'white' if sum(color) < color_threshold else 'black'
        x, y = g_embedding[node_id]
        x_min = min(x, x_min)
        y_min = min(y, y_min)
        x_max = max(x, x_max)
        y_max = max(y, y_max)
        node_num = idx_node + 1
        label = '%d' % (node_num)
        node_value = node_values[idx_node]
        node_size = __scale_node_size(node_value)
        custom_legend = m_lines.Line2D([0], [0], color='w', lw=0, marker='o', markersize=12, markeredgecolor='k', markerfacecolor=color, label=label)
        plt.plot(x, y, 'o', markersize=node_size, markeredgecolor='k', markerfacecolor=color)
        legend_handles.append(custom_legend)

        # also, plot text
        # plt.text(x, y, node_num, size=8, weight="bold", ha="center", va="center", color=text_color)

    offset = 2.8
    x_min = int(x_min) - offset
    x_max = round(x_max) + offset
    y_min = int(y_min) - offset
    y_max = round(y_max) + offset

    alphabets = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']
    title = '%02d %s' % (class_id, class_name)
    title = '(%s) %s' % (alphabets[class_id - 1], class_name)
    plt.tight_layout()
    plt.subplots_adjust(left=0.0, right=1.0, top=1.0, bottom=0.0)
    # plt.legend(bbox_to_anchor=(1.0, 1.0), handles=legend_handles)
    # plt.title(title)
    plt.title('')
    # plt.tight_layout()
    plt.xticks([])
    plt.yticks([])
    plt.xlim([x_min, x_max])
    plt.ylim([y_min, y_max])
    # plt.show()
    fig_num = class_id
    plt.savefig('/home/nour/Documents/Datasets/Breakfast/qualitative_results/breakfast_graphs/4-5-%s.png' % (fig_num))
    plt.savefig('/home/nour/Documents/Datasets/Breakfast/qualitative_results/breakfast_graphs/4-5-%s.pdf' % (fig_num))
    plt.clf()
    _ = 10

def __get_tensor_values(batch_size, keras_session, tensor, t_input_n, t_input_x, v_input_n, x):
    n_items = len(x)
    n_batches = utils.calc_num_batches(n_items, batch_size)

    data = None
    for idx_batch in range(n_batches):
        utils.print_counter(idx_batch + 1, n_batches)
        idx_b = idx_batch * batch_size
        idx_e = (idx_batch + 1) * batch_size
        v_input_x = x[idx_b:idx_e]
        print v_input_x.shape
        values, = keras_session.run([tensor], {t_input_x: v_input_x, t_input_n: v_input_n})  # (None, 1, 1, 64, 128)
        print values.shape
        print
        data = values if data is None else np.vstack((data, values))

    data = np.array(data)
    return data

def __load_model(model_name, epoch_num):
    model_root_path = Pth('Breakfast/models/%s', (model_name,))
    nodes_root_path = Pth('Breakfast/qualitative_results/node_embedding_%s' % (model_name,))
    custom_objects = {'tf': tf, 'ExpandDimsLayer': ExpandDimsLayer, 'MeanLayer': MeanLayer, 'MaxLayer': MaxLayer, 'TransposeLayer': TransposeLayer, 'ReshapeLayer': ReshapeLayer, 'DepthwiseConv1DLayer': DepthwiseConv1DLayer}
    json_path = '%s/%03d.json' % (model_root_path, epoch_num)
    weight_path = '%s/%03d.pkl' % (model_root_path, epoch_num)

    model = keras_utils.load_model(json_path, weight_path, custom_objects=custom_objects, is_compile=False)

    return model

def __plot_centroids(x, window_size, n_centroids, colors, fig_num):
    fig, ax = plt.subplots(nrows=1, ncols=1, num=fig_num, figsize=(4, 3))

    alpha_values = np.linspace(0.2, 0.8, window_size)
    ax.set_title('')

    # loop on all the features of the objects and visualize them
    for idx_window in range(window_size):

        alpha = alpha_values[idx_window]
        x_window = x[idx_window]

        for idx_centroid in range(n_centroids):
            color = colors[idx_centroid]
            ax.scatter([x_window[idx_centroid, 0]], [x_window[idx_centroid, 1]], s=20, c=color, lw=0, alpha=alpha)

    plt.tight_layout()
    plt.grid('on')
    plt.xticks([])
    plt.yticks([])
    plt.show()

def __async_tsne_embedding(x):
    # learn manifold
    tsne = MulticoreTSNE(n_jobs=32, n_components=2)
    x = x.astype(np.float64)
    x_fitted = tsne.fit_transform(x)

    return x_fitted

# endregion
