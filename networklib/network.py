#-*- coding:utf-8 -*-

'''
简介：
    用于对网络的分析，创建网络，计算网络特征等
        --利用get_edgedata_from_odrecord, get_graph_from_edgedata, get_graph_info等方法，
        直接从trip记录中计算网络图的特征
        --主函数对odrecord写好循环，便可以计算构建的对各网络图的特征
主要数据：

    edgedata:
        DataFrame;
        网络中边的信息，包含[Source,Target,Weight]信息,也可以是没有权重的

    cluster_result
        DataFrame;
        社区划分的结果，形式为['id','modularity_class'],参考gephi导出的结果

备注：
    2017.9.27.
        1.需要增加从graph对象到dataframe的方法，获取graph的边和节点表，参考pygrahistry的 network2pandas
            2017.10.10已增加 networkx2pandas方法

        2.结合igraph的社区发现，networkx的网络特征计算
            2017.10.10日已经增加计算模块度方法和社区发现方法

        3.接下来会补充一个example对各个数据的形式做一个展示

'''

import pandas as pd
import numpy as np
import graphistry
import igraph
import networkx as nx


class NetworkUnity():
    def __init__(self):
        pass

    @staticmethod
    def as_undirected_edgedata(edgedata):
        #将有向边转化为无向边
        index_droped = []
        edgedata_directed = edgedata.copy()
        for ind in edgedata.index:
            source = edgedata.ix[ind, 'Source']
            target = edgedata.ix[ind, 'Target']
            if ind not in index_droped:
                '''
                如果该边没有被丢弃过--例如之前在A-B这条边时,发现存在B-A,
                那么B-A这条边的index会被记录,之后会被丢弃
                '''
                data_target_as_source = edgedata[edgedata['Source'] == target]
                if len(data_target_as_source) >= 1:
                    if source in data_target_as_source['Target'].values:
                        index_2 = data_target_as_source[data_target_as_source['Target'] == source].index[0]
                        edgedata_directed.ix[ind, 'Weight'] += edgedata_directed.ix[index_2, 'Weight']
                        index_droped.append(index_2)
        #被丢弃的边数据
        # data_droped = edgedata.ix[index_droped,:]
        edgedata_directed.drop(index_droped, axis=0, inplace=True)
        return edgedata_directed

    @staticmethod
    def networkx2pandas(graph):
        '''
        :param graph: networkx.Graph/DiGraph
        :return: edgedata, DataFrame
        '''
        def _getedges(g):
            for es in list(g.edges(data=True)):
                yield dict({'Source': es[0], 'Target': es[1]}, **es[2])
        edgedata = pd.DataFrame(_getedges(graph))
        return edgedata

    @staticmethod
    def get_nodes_from_edgedata(edgedata,return_df=True):
        '''
        :param edgedata: 边的数据
        :param return_df: 是否返回Series，默认True，否则为list
        :return: 节点数据
        '''
        source = set(edgedata['Source'])
        target = set(edgedata['Target'])
        nodes = list(source.union(target))
        if return_df:
            nodes = pd.DataFrame(nodes,columns=['ID'])
        return nodes

    @staticmethod
    def get_graph_from_edgedata(edgedata, attr='Weight', directed=True,connected_component=False):
        '''
        :param edgedata: 边的数据
        :param attr: string 或 list; 边的属性数据，如果没有权重，设置attr=None，
        :param directed: 有向图还是无向图
        :param connected_component: 返回最大联通子图，默认为True,对于有向图为weakly_connected
                                    未开发

        :return: networkx.Graph 或 DiGraph
        '''
        if len(edgedata) < 1:
            if directed:
                return nx.DiGraph()
            else:
                return nx.Graph()

        if directed:
            graph = nx.from_pandas_dataframe(edgedata, 'Source', 'Target',
                                             edge_attr=attr, create_using=nx.DiGraph())
            if connected_component:
                #返回最大联通子图
                graph = max(nx.weakly_connected_component_subgraphs(graph), key=len)
        else:
            graph = nx.from_pandas_dataframe(edgedata, 'Source', 'Target',
                                             edge_attr=attr, create_using=nx.Graph())
            if connected_component:
                graph =  max(nx.connected_component_subgraphs(graph), key=len)

        print('Directed Graph ：', graph.is_directed())
        return graph

    @staticmethod
    def get_graph_info(graph,centrality=True,save_path=''):
        #用来计算图的各种网络特征，计算时间跟图的大小相关
        '''
        :param graph: graph对象,应该是连通的！
        :param centrality: 是否计算中心度信息
        :param save_path: 信息保存地址
        :return: graph的各种网络特征，pd.Series
        '''
        # connected = nx.connected_component_subgraphs
        def _average(node_dic):
            if len(node_dic) < 1:
                return 0
            else:
                return np.average(list(node_dic.values()))
        node_num = graph.number_of_nodes()
        edge_num = graph.number_of_edges()
        density = nx.density(graph)
        ave_degree = _average(graph.degree())
        infos = [node_num, edge_num, density, ave_degree]
        cols = [ 'NodeNum', 'EdgeNum', 'Density', 'AveDegree']
        #有向图和无向图
        if not graph.is_directed():
            directed = 0
            ave_clustering_coefficient = nx.average_clustering(graph)
            ave_shortest_path_length = nx.average_shortest_path_length()
            infos.extend([directed,ave_clustering_coefficient,ave_shortest_path_length])
            cols.extend(['Directed','AveClusterCoefficent','AveShortestPathLength'])
        else:
            ave_indegree = _average(graph.in_degree())
            ave_outdegree = _average(graph.out_degree())
            directed = 1
            #判断是否为空图
            infos.extend([directed,ave_indegree,ave_outdegree])
            cols.extend(['Directed','AveInDegree','AveOutDegree'])
        #中心性指标
        if centrality:
            #度中心性
            node_degree_centrality = nx.degree_centrality(graph)
            ave_degree_centrality = _average(node_degree_centrality)
            #介数中心度
            node_betweenness = nx.betweenness_centrality(graph)
            ave_betweenness_centrality = _average(node_betweenness)
            #接近中心度
            node_closeness = nx.closeness_centrality(graph)
            ave_closeness_centrality = _average(node_closeness)
            infos.extend([ave_degree_centrality,
                          ave_betweenness_centrality,
                          ave_closeness_centrality])
            cols.extend(['AveDegreeCentrality',
                            'AveBetweennessCentrality',
                            'AveClosenessCentrality'])

        graph_info = pd.Series(infos,index=cols)
        if len(save_path) != 0:
            graph_info.to_csv(save_path,index=True,header=None)
            print('File Saved : %s'%save_path)
        return graph_info

    @staticmethod
    def degree_filter(graph,lower=None,upper=None):
        '''
        :param graph: Networkx.Graph/DiGraph
        :param lower: int/float，the lower limitation of degree
        :param upper: int/float，the upper limitation of degree
        :return: graph after filter
        '''
        node_degree = graph.degree()
        nodes_all = list(graph.nodes())
        print('Node num: ',graph.number_of_nodes())
        data = pd.DataFrame(list(node_degree),columns=['ID','Degree'])

        if lower is not None:
            data = data[data['Degree'] >= lower]
        if upper is not None:
            data = data[data['Degree'] <= upper]
        nodes_saved = list(data['ID'])
        nodes_drop = set(nodes_all).difference(nodes_saved)
        graph.remove_nodes_from(nodes_drop)
        print('Node num: ',graph.number_of_nodes())
        return graph

    @staticmethod
    def draw_graph(graph,nodes=None):
        '''
        采用pygraphistry 来绘制网络图，节点颜色目前还不能超过12种
        :param graph: networkx.Graph/DiGraph
        :param nodes: DataFrame,如果需要按社区颜色绘制，请传入带有社区信息的节点表, ['ID','modulraity_class']
        :return: None
        '''
        graphistry.register(key='contact pygraphistry for api key')

        ploter = graphistry.bind(source='Source', destination='Target').graph(graph)
        if nodes is not None:
            ploter = ploter.bind(node='ID', point_color='modularity_class').nodes(nodes)
        ploter.plot()
        return None

    @staticmethod
    def community_detect(graph=None,edgedata=None,directed=True,
                         use_method=1, use_weight=None):
        '''
        :param edgedata: DataFrame, 边的数据
        :param graph: Networkx.Graph/DiGraph，与edgedata给定一个就行
        :param directed: Bool, 是否有向
        :param use_method: Int, 使用方法
        :param weight_name: String, 社区发现算法是否使用边权重，如果使用,例如weight_name='Weight'
        :return: 带有社区信息的节点表格
        '''
        #创建igraph.Graph类
        if graph is None and edgedata is not None:
            graph = NetworkUnity.get_graph_from_edgedata(edgedata,
                                                         directed=directed,connected_component=True)

        gr = graphistry.bind(source='Source', destination='Target', node='ID', edge_weight='Weight').graph(graph)
        edgedata = NetworkUnity.networkx2pandas(graph)
        ig = gr.pandas2igraph(edgedata, directed=directed)

        #--------------------------------------------------------
        #如果使用边的数据edgedata
        # gr = graphistry.bind(source='Source',destination='Target',edge_weight='Weight').edges(edgedata)
        # nodes = NetworkUnity.get_nodes_from_edgedata(edgedata)
        # gr = gr.bind(node='ID').nodes(nodes)
        # ig = gr.pandas2igraph(edgedata,directed=directed)
        # --------------------------------------------------------

        '''
        关于聚类的方法，
        参考http://pythonhosted.org/python-igraph/igraph.Graph-class.html
        希望以后可以对每一个算法添加一些简单的介绍
        '''
        method_dict = {
            0:'''ig.community_fastgreedy(weights='%s')'''%str(use_weight),
            1:'''ig.community_infomap(edge_weights='%s',trials=10)'''%str(use_weight),
            2:'''ig.community_leading_eigenvector_naive(clusters=10)''',
            3:'''ig.community_leading_eigenvector(clusters=10)''',
            4:'''ig.community_label_propagation(weights='%s')'''%str(use_weight),
            5:'''ig.community_multilevel(weights='%s')'''%str(use_weight),
            6:'''ig.community_optimal_modularity()''',
            7:'''ig.community_edge_betweenness()''',
            8:'''ig.community_spinglass()''',
            }

        detect_method = method_dict.get(use_method)

        if use_weight is None:
            #如果为None,需要把公式里面的冒号去掉,注意如果有多个None,这个方法需要重新写
            detect_method= detect_method.replace('\'','')
        print('社区发现方法： ',detect_method)
        #开始实施社区发现算法
        res_community = eval(detect_method)
        #将社区信息保存到节点信息中
        ig.vs['modulraity_class'] = res_community.membership
        #将节点信息转化为Dataframe表
        edgedata_,nodedata = gr.igraph2pandas(ig)
        modularity = res_community.modularity
        print(res_community.summary())
        print('community size:\n', res_community.sizes())
        print('modularity:\n', modularity)
        return nodedata

    @staticmethod
    def modularity(cluster_rescult,edgedata=None,graph=None,
                       directed=True, edge_weight='Weight'):
        '''
        :param cluster_rescult: 聚类结果，参考gephi输出的表，[id,modulraity_class]
        :param edgedata: 边数据，与graph给定其中一个
        :param graph: networkx中的Graph/DiGraph
        :param directed: 是否为有向图
        :param edge_weight:
            None/str, 计算模块度是否使用边的权重，如果使用，给定边权重的name
            例如edge_weight='Weight'
            如果不使用，请给定为None
        :return: Q值
        ps：
            1.edgedata 和 graph 至少要给定一个
            2.与gephi中计算的模块度结果已经对比过了，结果一致
        '''
        if edgedata is None and graph is not None:
            edgedata = NetworkUnity.networkx2pandas(graph)

        gr = graphistry.bind(source='Source', destination='Target',
                             node='ID',edge_weight=edge_weight)

        ig = gr.pandas2igraph(edgedata,directed=directed)
        nodes = pd.DataFrame(list(ig.vs['ID']), columns=['ID'])
        community_data = pd.merge(nodes, cluster_rescult, left_on='ID', right_on='id', how='left')

        if edge_weight is None:
            Q = ig.modularity(list(community_data['modularity_class']),weights=None)
        else:
            Q = ig.modularity(list(community_data['modularity_class']),weights=list(ig.es[edge_weight]))
        return Q


#------------------examples
def main_filter():
    DataDir = r'G:\data\transport\tokyo\Tokyo_2008_Original\Processed\grid\grid7000'
    edgepath = DataDir + '\\edgedata.csv'
    edgedata = pd.read_csv(edgepath)
    graph = NetworkUnity.get_graph_from_edgedata(edgedata, connected_component=True)

    NetworkUnity.degree_filter(graph)

def main_function():
    DataDir = r'G:\data\transport\tokyo\Tokyo_2008_Original\Processed\grid\grid7000'
    edgepath = DataDir + '\\edgedata.csv'
    edgedata = pd.read_csv(edgepath)
    graph = NetworkUnity.get_graph_from_edgedata(edgedata,connected_component=True)
    sv_info = DataDir + 'graph_info.csv'
    infos = NetworkUnity.get_graph_info(graph,centrality=True,save_path=sv_info)

    # NetworkUnity.draw_graph(NetworkUnity,graph)

def main_modularity():
    DataDir = r'G:\data\transport\tokyo\Tokyo_2008_Original\Processed\grid\grid7000'
    edgepath = DataDir + '\\edgedata.csv'
    edgedata = pd.read_csv(edgepath)

    res_path = DataDir + '\\cluster\\cluster_result_unweight.csv'
    res_cluster = pd.read_csv(res_path)
    q = NetworkUnity.modularity(res_cluster,edgedata=edgedata,directed=True,edge_weight=None)
    print(q)

def main_cluster():
    DataDir = r'G:\data\transport\tokyo\Tokyo_2008_Original\Processed\grid\grid7000'
    edgepath = DataDir + '\\edgedata.csv'
    edgedata = pd.read_csv(edgepath)
    graph = NetworkUnity.get_graph_from_edgedata(edgedata,connected_component=True)
    graph = NetworkUnity.degree_filter(graph,5)
    nodedata_1 = NetworkUnity.community_detect(graph, use_method=1, use_weight=None)
    print(nodedata_1.head())


if __name__ == '__main__':
    import time
    time_1 = time.clock()
    main_cluster()
    # main_modularity()
    # main_filter()
    print('---------RunTime----------')
    print('%.3f s'%(time.clock()-time_1))


