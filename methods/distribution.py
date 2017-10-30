'''
简介：
    对数据的分布进行拟合
    即，概率密度函数符合哪种分布！！！ 并不是曲线拟合！！
        基于scipy.optimize曲线拟合模型
        目前支持：
            * 幂率分布
            * 对数正太
            * 指数分布
            * 韦布尔分布
            * 伽马分布
            * 指数阶段的幂率分布

方法：
    分布拟合 - FitModel.fit
    绘制拟合 - FitMofel.plot_model


数据：
    data, 为pandas.Series数据类型

备注：

    * 2017.10.27
        目前只是数据的分布进行拟合，后面可以再扩展成曲线的拟合较好
        绘制方法还需要改进
        支持的分布需要继续增加

'''

import numpy as np
import scipy.stats
import pandas as pd
from scipy.special import gamma as gammafunction
from scipy import optimize
import matplotlib.pyplot as plt


class FitModel():
    DISTRIBUTION = ['powerlaw',
                    'exponential',
                    'gamma',
                    'lognormal',
                    'weibull',
                    'exponential_powerlaw']

    INIT_PARA_DIC = {'powerlaw': [1,1.5],
                     'exponential': [2],
                     'gamma': [1, 2],
                     'lognormal': [3, 2],
                     'weibull': [1, 2],
                     'exponential_powerlaw':[5.3,1.5,0.9]}

    DISTRIBUTION_DIC = {each: 'FitModel.' + each for each in DISTRIBUTION}

    def __init__(self, data=None):
        '''
        :param data: 数据为pd.Series数据
        '''
        self.origin_data = data
        if data is not None:
            self.data_pdf = FitModel.distribution_pdf(data)
        self.summary = []

    # ----------------------------------------------------------------------------
    @staticmethod
    def powerlaw(x, a, beta):
        return a * (x ** (-beta))

    @staticmethod
    def lognormal(x, mu, sigmma):
        return 1 / (x * sigmma * np.sqrt(2 * np.pi)) * np.exp(((np.log(x) - mu) ** 2) / (-2 * sigmma * sigmma))

    @staticmethod
    def exponential(x, lam):
        return np.exp(-lam * x)

    @staticmethod
    def weibull(x, alpha, beta):
        '''对比一致'''
        return (alpha / beta) * ((x / beta) ** (alpha - 1)) * np.exp(-((x / beta) ** alpha))

    @staticmethod
    def gamma(x, alpha, beta):
        '''检测一致'''
        return ((beta ** alpha) / gammafunction(alpha)) * (x ** (alpha - 1)) * np.exp(-beta * x)

    @staticmethod
    def exponential_powerlaw(x, x0, beta, alpha):
        return (x + x0) ** (-beta) * np.exp(-alpha * x)

    # ----------------------------------------------------------------------------

    @staticmethod
    def distribution_pdf(data):
        '''
            计算数据的概率密度分布
            :param data: list 或者 pandas.Series.
            :return: pandas.Series
            '''
        if data is None:
            return None
        if not isinstance(data, pd.Series):
            data = pd.Series(data)
        data_count = data.value_counts().sort_index()
        data_p = data_count / data_count.sum()
        return data_p

    def fit(self, distribution, data=None, x_max=None, x_min=None, initial_para=None):
        '''
        对数据的概率密度分布进行拟合。
        拟合的信息会保存成Dict,包括:'distribution','popt', 'pcov', 'data_pdf','xdata','ydata'
        保存到模型的summary 中，以便查询和绘制结果

        :param distribution: 分布名称
        :param data: 需要分布拟合的数据
        :param x_max: 拟合分布图像的上限
        :param x_min: 拟合分布图像的下限
        :param initial_para: 拟合分布初始参数
        :return: 拟合的信息，dict
        '''
        if initial_para is None:
            if distribution in FitModel.INIT_PARA_DIC.keys():
                initial_para = FitModel.INIT_PARA_DIC.get(distribution)
            else:
                print('- - 拟合的分布未定义 - - ')
                return None

        if data is None:
            if self.origin_data is None:
                print('- - Data is None - -')
                return None
            else:
                data_pdf = self.data_pdf
        else:
            data_pdf = FitModel.distribution_pdf(data)

        if x_max is not None:
            data_pdf = data_pdf[data_pdf.index < x_max].copy()

        if x_min is not None:
            data_pdf = data_pdf[data_pdf.index > x_min].copy()

        xdata_fit = data_pdf.index.values
        ydata_fit = data_pdf.values

        fit_distribution = FitModel.DISTRIBUTION_DIC.get(distribution)

        popt, pcov = optimize.curve_fit(eval(fit_distribution), xdata_fit, ydata_fit, p0=initial_para)

        fit_info = {'distribution': fit_distribution,
                    'popt': popt,
                    'pcov': pcov,
                    'data_pdf':data_pdf,
                    'xdata': xdata_fit,
                    'ydata': ydata_fit}
        self.summary.append(fit_info)

        print('------------ 拟合分布 %s -------------' % fit_distribution)
        print('- - Optimal Parameters : ',popt)
        print('-Estimated Covariance : ',pcov)
        return fit_info

    def plot_model(self,log_log=True,style=0, mfrow=None):
        '''
        :param log_log: 是否为log_log
        :param style: 绘制的风格
            0 - 所有拟合绘制在一起
            1 - 拟合结果分多个ax绘制
        :param mfrow: 图片分割方式，如果style为1的话，可以指定
        :return:
        '''
        if len(self.summary) < 1:
            print('- - 模型还没有拟合 - - ')
            return None

        fig = plt.figure()
        if style == 0:
            ax = fig.add_subplot(1, 1, 1)
            ax.plot(self.data_pdf.index.values, self.data_pdf.values, 'k+')
            for model in self.summary:
                xdata = model.get('xdata')
                para = model.get('popt')
                distribution = model.get('distribution')
                fit_funtion = model.get('distribution') + '(xdata, *para)'
                ydata = eval(fit_funtion)

                ax.plot(xdata, ydata, label=distribution.replace('FitModel.', ''))
                ax.legend()
            ax.set_ylabel('Pr')
            if log_log:
                ax.set_yscale('log')
                ax.set_xscale('log')
        if style == 1:
            model_num = len(self.summary)
            if mfrow is None:
                # 设置图片分割方式，如果没有的话
                if model_num < 3:
                    mfrow = (1, model_num)
                elif model_num < 7:
                    mfrow = (2, 3)
                else:
                    mfrow = (3, 3)
            # 开始绘制每一个ax
            axes = []
            for i, model in enumerate(self.summary):
                axes.append(fig.add_subplot(mfrow[0], mfrow[1], i + 1))
                xdata = model.get('xdata')
                para = model.get('popt')
                distribution = model.get('distribution')
                fit_funtion = model.get('distribution') + '(xdata, *para)'
                ydata = eval(fit_funtion)
                axes[i].plot(self.data_pdf.index.values, self.data_pdf.values, '*')
                axes[i].plot(xdata, ydata, label=distribution.replace('FitModel.', ''))
                axes[i].legend()
                axes[i].set_ylabel('Pr')
                if log_log:
                    axes[i].set_yscale('log')
                    axes[i].set_xscale('log')
        plt.show()


def test():
    xdata = np.linspace(0.1, 2.5, 100)
    lis_1 = [FitModel.weibull(x, 0.5, 1) for x in xdata]
    lis_2 = [FitModel.weibull(x, 1.5, 1) for x in xdata]
    lis_3 = [FitModel.weibull(x, 5, 1) for x in xdata]

    plt.plot(lis_1)
    plt.plot(lis_2)
    plt.plot(lis_3)
    plt.show()


def test_model():
    DataDir = r'G:\data'
    path_dis = DataDir + '\\DistanceAC.csv'
    data = pd.read_csv(path_dis, header=0)
    data = data['DistanceAC']
    data = data[data > 0]
    # -----------------------------------------------
    model = FitModel(data=data)

    model.fit(distribution='exponential', x_max=8)
    model.fit(distribution='lognormal')
    model.fit(distribution='gamma')

    model.plot_model(style=1)

if __name__ == '__main__':
    test_model()



