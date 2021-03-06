# -*- coding: utf-8 -*-
#
#  Copyright 2016, 2017 Ramil Nugmanov <stsouko@live.ru>
#  This file is part of CIMtools.
#
#  CIMtools is free software; you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#
from CGRtools.files.RDFrw import RDFread
from copy import deepcopy
from pandas import read_csv
from .estimators.kernels import tanimoto_kernel


class MBparser(object):
    def __parse_svm_opts(self, param, op, unpac=lambda x: x):
        res = []
        commaparam = param.split(',')
        for i in commaparam:
            ddotparam = i.split(':')
            if len(ddotparam) == 1:
                if i[0] == '^':
                    res.append(unpac(op(i[1:])))
                else:
                    res.append(op(i))
            elif len(ddotparam) >= 3:
                if i[0] == '^':
                    res.extend([unpac(x) for x in self.__drange(op(ddotparam[0][1:]),
                                                                op(ddotparam[1]), int(ddotparam[2]))])
                else:
                    res.extend([x for x in self.__drange(op(ddotparam[0]), op(ddotparam[1]), int(ddotparam[2]))])

        return res

    @staticmethod
    def __drange(start, stop, step):
        r = start
        s = (stop - start) / (step - 1)
        res = []
        while r <= stop:
            res.append(r)
            r += s
        return res

    @staticmethod
    def __pow10(x):
        return pow(10, x)

    __kernel = {'0': 'linear', '1': 'poly', '2': 'rbf', '3': 'sigmoid', 't': 'tanimoto'}

    def get_svm_param(self, files):
        res = []
        repl = {'-t': ('kernel', lambda x: [self.__kernel[x] for x in x.split(',')]),
                '-c': ('C', lambda x: self.__parse_svm_opts(x, float, unpac=self.__pow10)),
                '-d': ('degree', lambda x: self.__parse_svm_opts(x, int)),
                '-e': ('tol', lambda x: self.__parse_svm_opts(x, float, unpac=self.__pow10)),
                '-p': ('epsilon', lambda x: self.__parse_svm_opts(x, float, unpac=self.__pow10)),
                '-g': ('gamma', lambda x: self.__parse_svm_opts(x, float, unpac=self.__pow10)),
                '-r': ('coef0', lambda x: self.__parse_svm_opts(x, float))}
        for file in files:
            svm = {}
            with open(file) as f:
                for line in (x for x in f if x.strip()):
                    opts = line.split()
                    parsed = dict(kernel=['rbf'], C=[1.0], epsilon=[.1], tol=[.001], degree=[3], gamma=[1.0], coef0=[0])
                    for x, y in zip(opts[::2], opts[1::2]):
                        z = repl.get(x)
                        if z:
                            parsed[z[0]] = z[1](y)

                    for i in parsed['kernel']:
                        tmp = deepcopy(parsed)
                        if i == 'linear':  # u'*v
                            if svm.get(i):
                                for k in ('C', 'epsilon', 'tol'):
                                    svm[i][k].extend(tmp[k])
                            else:
                                svm[i] = dict(kernel=[i], C=tmp['C'], epsilon=tmp['epsilon'],
                                              tol=tmp['tol'])
                        elif i == 'rbf':  # exp(-gamma*|u-v|^2)
                            if svm.get(i):
                                for k in ('C', 'epsilon', 'tol', 'gamma'):
                                    svm[i][k].extend(tmp[k])
                            else:
                                svm[i] = dict(kernel=[i], C=tmp['C'], epsilon=tmp['epsilon'], tol=tmp['tol'],
                                              gamma=tmp['gamma'])
                        elif i == 'sigmoid':  # tanh(gamma*u'*v + coef0)
                            if svm.get(i):
                                for k in ('C', 'epsilon', 'tol', 'gamma', 'coef0'):
                                    svm[i][k].extend(tmp[k])
                            else:
                                svm[i] = dict(kernel=[i], C=tmp['C'], epsilon=tmp['epsilon'],
                                              tol=tmp['tol'], gamma=tmp['gamma'], coef0=tmp['coef0'])
                        elif i == 'poly':  # (gamma*u'*v + coef0)^degree
                            if svm.get(i):
                                for k in ('C', 'epsilon', 'tol', 'gamma', 'coef0', 'degree'):
                                    svm[i][k].extend(tmp[k])
                            else:
                                svm[i] = dict(kernel=[i], C=tmp['C'], epsilon=tmp['epsilon'], tol=tmp['tol'],
                                              gamma=tmp['gamma'], coef0=tmp['coef0'], degree=tmp['degree'])
                        elif i == 'tanimoto':
                            if svm.get(i):
                                for k in ('C', 'epsilon', 'tol'):
                                    svm[i][k].extend(tmp[k])
                            else:
                                svm[i] = dict(kernel=[tanimoto_kernel],
                                              C=tmp['C'], epsilon=tmp['epsilon'], tol=tmp['tol'])

            if svm:
                res.append(svm)
        if not res:
            raise Exception('Incorrect SVM config files')
        return res

    @staticmethod
    def parse_model_description(file):
        tmp = {}
        with open(file) as f:
            for line in f:
                k, v = (x.strip() for x in line.split(':='))
                if k in ('nlim', 'tol', 'name', 'example', 'description', 'report_units', 'show_structures'):
                    if k in ('nlim', 'tol'):
                        v = float(v)
                    tmp[k] = v
        return tmp

    @staticmethod
    def parse_fragmentor_opts(file):
        params = []
        with open(file) as f:
            for line in (x for x in f if x.strip()):
                opts = line.split()
                tmp = {}
                for x in opts:
                    key, value = (x.strip() for x in x.split('='))
                    value = True if value == 'True' else False if value == 'False' else value
                    if key in ['header']:
                        tmp[key] = [x.strip() for x in value.split('|')]
                    elif key in ('cgr_marker', 'cgr_b_templates', 'cgr_m_templates'):
                        with open(value) as vf:
                            tmp[key] = RDFread(vf).read()
                    elif key in ('marker_rules', 'standardize', 'docolor',
                                 'cgr_marker_preprocess', 'cgr_marker_postprocess'):
                        with open(value) as vf:
                            tmp[key] = vf.read()
                    else:
                        tmp[key] = value
                params.append(tmp)
        return params

    @staticmethod
    def parse_ext(rawext):
        extdata = {}
        s_option = None
        for e in rawext:
            ext, *add = e.split(':')
            if ext == 's_option':
                if add:
                    s_option = add[0]
            elif add:
                tmp = read_csv(add[0])
                k = tmp.pop('EXTKEY')
                v = tmp.rename(columns=lambda x: '%s.%s' % (ext, x))
                extdata[ext] = {x: y.to_dict() for x, (_, y) in zip(k, v.iterrows())}
            else:
                extdata[ext] = None
        return dict(s_option=s_option, data=extdata)
