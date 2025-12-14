import os
import numpy as np
import scipy.io as io
from pyx import *
from pdf2image import convert_from_path

tex = text.set(text.LatexEngine,texenc='utf-8')
text.preamble(r"\renewcommand{\sfdefault}{phv}")

#-----------------------------------------------------#
colorbar = color.cmykgradient.ReverseRainbow
inds0 = np.linspace(0.1,0.9,4)
colors0 = []
for ind in inds0:
    colors0.append(colorbar.getcolor(ind))

colorbar = color.cmykgradient.Jet
inds0 = np.linspace(0,1,8)
colors1 = []
for ind in inds0:
    colors1.append(colorbar.getcolor(ind))

bwr_r = color.functiongradient_rgb(
    f_r=lambda x:  4.9*(x)**4 - 10*(x)**3 + 4.9*(x)**2 - 0.58*(x) + 0.9,
    f_g = lambda x: 13*(x)**4 - 26*(x)**3 + 13*(x)**2 - 0.15*(x) + 0.2,
    f_b = lambda x: 6.4*(x)**4 - 13*(x)**3 + 6.3*(x)**2 + 0.99*(x) + 0.054)

bwr = color.functiongradient_rgb(
    f_r=lambda x:  4.9*(1-x)**4 - 10*(1-x)**3 + 4.9*(1-x)**2 - 0.58*(1-x) + 0.9,
    f_g = lambda x: 13*(1-x)**4 - 26*(1-x)**3 + 13*(1-x)**2 - 0.15*(1-x) + 0.2,
    f_b = lambda x: 6.4*(1-x)**4 - 13*(1-x)**3 + 6.3*(1-x)**2 + 0.99*(1-x) + 0.054)

parula = color.functiongradient_rgb(
    f_r=lambda x:  -21.4*(1-x)**4 + 40.7*(1-x)**3 - 22.1*(1-x)**2 + 3.46*(1-x) + 0.13,
    f_g = lambda x: 7.885*(1-x)**4 - 14.36*(1-x)**3 + 7.091*(1-x)**2 + 0.2187*(1-x) + 0.15,
    f_b = lambda x: 0.02211*(1-x)**4 +5.409*(1-x)**3 -9.264*(1-x)**2 + 3.35*(1-x) + 0.63)

bwr_lighter = color.functiongradient_rgb(
   f_r=lambda x:  4.874*(1-x)**4 -8.174*(1-x)**3 +1.595*(1-x)**2 +1.186*(1-x) + 0.6,
    f_g = lambda x: 7.064*(1-x)**4 -15.11*(1-x)**3 +6.937*(1-x)**2 +1.328*(1-x) + 0.016,
    f_b = lambda x: 5.706*(1-x)**4 -15.56*(1-x)**3 +11.76*(1-x)**2 - 1.55*(1-x) + 0.196)

bwr_darker = color.functiongradient_rgb(
    f_r=lambda x:  7.308*(1-x)**4 -12.22*(1-x)**3 +2.899*(1-x)**2 + 1.585*(1-x) + 0.4755,
    f_g = lambda x: 10.15*(1-x)**4 - 20.81*(1-x)**3 + 10.36*(1-x)**2 + 0.5829*(1-x) + 0.05,
    f_b = lambda x: 9.461*(1-x)**4 -21.49*(1-x)**3 +13.52*(1-x)**2 - 1.132*(1-x) + 0.1528)

bwr_ligest = color.functiongradient_rgb(
    f_r=lambda x:  5.1*(1-x)**4 - 10*(1-x)**3 +5*(1-x)**2 - 0.7*(1-x) + 0.95,
    f_g = lambda x: 5*(1-x)**4 -10*(1-x)**3 +4.9*(1-x)**2 +0.29*(1-x) + 0.52,
    f_b = lambda x: 4.9*(1-x)**4 -9.9*(1-x)**3 +4.9*(1-x)**2 +0.87*(1-x) + 0.2)

class changesymbol(graph.style.symbol):

    def __init__(self, sizecolumnname="size", colorcolumnname="color",
                       gradient=bwr_r,
                       symbol=graph.style.symbol.circle,
                       symbolattrs=[style.linewidth.thin],#,deco.filled
                       **kwargs):
        # add some configuration parameters and modify some other
        self.sizecolumnname = sizecolumnname
        self.colorcolumnname = colorcolumnname
        self.gradient = gradient
        graph.style.symbol.__init__(self, symbol=symbol, symbolattrs=symbolattrs, **kwargs)

    def columnnames(self, privatedata, sharedata, agraph, columnnames, dataaxisnames):
        # register the new column names
        if self.sizecolumnname not in columnnames:
            raise ValueError("column '%s' missing" % self.sizecolumnname)
        if self.colorcolumnname not in columnnames:
            raise ValueError("column '%s' missing" % self.colorcolumnname)
        return ([self.sizecolumnname, self.colorcolumnname] +
                graph.style.symbol.columnnames(self, privatedata, sharedata, agraph,
                                               columnnames, dataaxisnames))

    def drawpoint(self, privatedata, sharedata, graph, point):
        # replace the original drawpoint method by a slightly revised one
        if sharedata.vposvalid and privatedata.symbolattrs is not None:
            x_pt, y_pt = graph.vpos_pt(*sharedata.vpos)
            color = self.gradient.getcolor(point[self.colorcolumnname])
            privatedata.symbol(privatedata.symbolcanvas, x_pt, y_pt,
                               privatedata.size_pt*point[self.sizecolumnname],
                               privatedata.symbolattrs + [color])

#-----------------------------------------------------#
# LOAD DATA
#-----------------------------------------------------#
print('='*60,'Plotting Figure')
print('-'*40,'Load data')

# the berry curvature and spin berry curvature
fa_kps, fa_omega1, fa_omega_s1 = io.loadmat('amqsh_BC_1D.mat')['kps'], io.loadmat('amqsh_BC_1D.mat')['Omega'],io.loadmat('amqsh_BC_1D.mat')['Omega_s']
# bulk bands for non-SOC in figure b
kpsb1,Esb1 = io.loadmat('amqsh_band1d.mat')['kps'],io.loadmat('amqsh_band1d.mat')['Es']
# bulk bands for SOC in figure b
fa_kps, fa_omega2, fa_omega_s2 = io.loadmat('amqsh_type1_BC_1D.mat')['kps'], io.loadmat('amqsh_type1_BC_1D.mat')['Omega'],io.loadmat('amqsh_type1_BC_1D.mat')['Omega_s']

kpsb1,Esb1 = io.loadmat('amqsh_band1d.mat')['kps'],io.loadmat('amqsh_band1d.mat')['Es']

# spin-hall conductivity
xs_Es1, ys_shc1 = io.loadmat('amqsh_shc.mat')['xs'][0],io.loadmat('amqsh_shc.mat')['ys'][0]*(-1)

xs_Es2, ys_shc2 = io.loadmat('amqsh_type1_shc.mat')['xs'][0],io.loadmat('amqsh_type1_shc.mat')['ys'][0]*(-1)
# the universal kps
kps = kpsb1
#----------------------------------------------------#
print('-'*40,'Figures setting')
w0 = 4
h0 = 4.1

wspace = 0.4
hspace = 1

xlabel_a = r'$E_F$ (meV)'
ylabel_a = r'$E$ (eV)'

xlabel_b = r'$E_F$ (meV)'
ylabel_b = r'$E$ (eV)'

xmin_cdef,xmax_cdef = -1,1
ymin_cdef,ymax_cdef = -0.2,0.2

xlabel_cdef = r'$k_x/\pi$'
ylabel_cdef = r'$E$ (eV)'

yminab,ymaxab = -1,1
xminab,xmaxab = 0,kps[3,:].max()
yminef,ymaxef = -1,1

#-------------------------------
# a/ c/ e/
# b/ d/ f/
#-------------------------------

titlesize = text.size.small
labelsize = text.size.small

c = canvas.canvas()
mypainter_xall = graph.axis.painter.regular(innerticklength=None,outerticklength=None,titledist=0.1*unit.v_cm,titlepos=0.5,labeldist=0.05*unit.v_cm,labelattrs=[labelsize ],titleattrs=[titlesize])
mypainter_yall = graph.axis.painter.regular(titledist=0.1*unit.v_cm,titlepos=0.5,labeldist=0.05*unit.v_cm,labelattrs=[labelsize ],titleattrs=[titlesize])
mypainter_colorbar = graph.axis.painter.regular(titledist=-0.2*unit.v_cm,titlepos=0.5,labeldist=0.05*unit.v_cm,labelattrs=[labelsize ],titleattrs=[titlesize])

myticksx = [graph.axis.tick.tick(0,label=r'$\mathrm{M}$'),graph.axis.tick.tick(kps[1,:][0],label=r'$\mathrm{X}$'),\
            graph.axis.tick.tick(kps[2,:][0],label=r'$\mathrm{\Gamma}$'),graph.axis.tick.tick(kps[3,:][0],label=r'$\mathrm{Y}$'),graph.axis.tick.tick(kps[3,:].max(),label=r'$\mathrm{M}$')]

mypainter_yall_b = graph.axis.painter.regular(titledist=-0.3*unit.v_cm,titlepos=0.65,labeldist=0.05*unit.v_cm,labelattrs=[labelsize ],titleattrs=[titlesize])
mypainter_yall_a = graph.axis.painter.regular(titledist=-0.25*unit.v_cm,titlepos=0.5,labeldist=0.05*unit.v_cm,labelattrs=[labelsize ],titleattrs=[titlesize])

ga = c.insert(graph.graphxy(width=w0,height=h0,
		x = graph.axis.linear(min=0,max=kps[3,:].max(),title=None,manualticks=myticksx,painter=mypainter_xall),
                  x2 = graph.axis.linear(min=0,max=kps[3,:].max(),title=None,parter=None),
                   y = graph.axis.linear(min=-1,max=1,title=r'$E-E_F$ (eV)',parter = graph.axis.parter.linear(['1','0.5']),painter=mypainter_yall_a),
                    y2 = graph.axis.linear(min=-1,max=1,title=None,parter=None),
                   ))
ga2 = c.insert(graph.graphxy(width=w0*0.35,height=h0,xpos=w0,
		x = graph.axis.linear(min=-2.5,max=0.8,title=r'$\sigma_s\,(e/4\pi)$',parter = graph.axis.parter.linear(['2','1']),
        painter=mypainter_xall),
                  x2 = graph.axis.linkedaxis(ga.axes["x2"]),
		y = graph.axis.linkedaxis(ga.axes["y"]),
                    y2 = graph.axis.linkedaxis(ga.axes["y2"]),
                   ))

ga.plot(graph.data.function('x(y)='+str(kps[1,:][0]),min=-1.1,max=1.1,title=None),
         styles=[graph.style.line(lineattrs=[color.cmyk.Gray,style.linewidth.thick,style.linestyle.solid])])
ga.plot(graph.data.function('x(y)='+str(kps[2,:][0]),min=-1.1,max=1.1,title=None),
         styles=[graph.style.line(lineattrs=[color.cmyk.Gray,style.linewidth.thick,style.linestyle.solid])])
ga.plot(graph.data.function('x(y)='+str(kps[3,:][0]),min=-1.1,max=1.1,title=None),
         styles=[graph.style.line(lineattrs=[color.cmyk.Gray,style.linewidth.thick,style.linestyle.solid])])

gb = c.insert(graph.graphxy(width=w0,height=h0,xpos = w0*1.35+wspace,
		x = graph.axis.linear(min=0,max=kps[3,:].max(),title=None,manualticks=myticksx,painter=mypainter_xall),
                  x2 = graph.axis.linkedaxis(ga.axes["x2"]),
		y = graph.axis.linkedaxis(ga.axes["y"]),
                    y2 = graph.axis.linkedaxis(ga.axes["y2"]),
                   ))
gb2 = c.insert(graph.graphxy(width=w0*0.35,height=h0,xpos=w0*2.35+wspace,
		x = graph.axis.linear(min=-2.5,max=0.8,title=r'$\sigma_{xy}\,(e/4\pi)$',parter = graph.axis.parter.linear(['2','1']),
        painter=mypainter_xall),
                  x2 = graph.axis.linkedaxis(ga.axes["x2"]),
		y = graph.axis.linkedaxis(ga.axes["y"]),
                    y2 = graph.axis.linkedaxis(ga.axes["y2"]),
                   ))

gb.plot(graph.data.function('x(y)='+str(kps[1,:][0]),min=-1.1,max=1.1,title=None),
         styles=[graph.style.line(lineattrs=[color.cmyk.Gray,style.linewidth.thick,style.linestyle.solid])])
gb.plot(graph.data.function('x(y)='+str(kps[2,:][0]),min=-1.1,max=1.1,title=None),
         styles=[graph.style.line(lineattrs=[color.cmyk.Gray,style.linewidth.thick,style.linestyle.solid])])
gb.plot(graph.data.function('x(y)='+str(kps[3,:][0]),min=-1.1,max=1.1,title=None),
         styles=[graph.style.line(lineattrs=[color.cmyk.Gray,style.linewidth.thick,style.linestyle.solid])])

# ga2.plot(graph.data.values(x=ys_shc1,y=xs_Es1),styles=[graph.style.line(lineattrs=[color.cmyk.Green,style.linestyle.solid,style.linewidth.THick])])
# gb2.plot(graph.data.values(x=ys_shc2,y=xs_Es2),styles=[graph.style.line(lineattrs=[color.cmyk.Blue,style.linestyle.solid,style.linewidth.THick])])


nbands,nk,norbs = Esb1.shape

# for i in range(nbands):
#     ga.plot(graph.data.values(x=fa_kps[i,:],y=fa_omega_s1[i,:]/abs(fa_omega_s1.min())*0.3-0.15),styles=[graph.style.line(lineattrs=[color.cmyk.Black,
#                                              style.linestyle.solid,style.linewidth.Thick])])
#     ga.plot(graph.data.values(x=fa_kps[i,:],y=fa_omega1[i,:]/abs(fa_omega1.min())*0.5+0.15),styles=[graph.style.line(lineattrs=[color.cmyk.Black,
#                                              style.linestyle.dashed,style.linewidth.Thick])])


# for i in range(nbands):
#     gb.plot(graph.data.values(x=fa_kps[i,:],y=fa_omega_s2[i,:]/abs(fa_omega_s2.min())*0.3-0.15),styles=[graph.style.line(lineattrs=[color.cmyk.Black,
#                                              style.linestyle.solid,style.linewidth.Thick])])
#     gb.plot(graph.data.values(x=fa_kps[i,:],y=fa_omega2[i,:]/abs(fa_omega2.max())*0.5+0.15),styles=[graph.style.line(lineattrs=[color.cmyk.Black,
#                                              style.linestyle.dashed,style.linewidth.Thick])])




# c.text(-txtposlr-0,h0-textposud,r"\textsf{(c)}",[text.halign.center,text.size.large])
# c.text(w0*1.67-txtposlr-0.4,h0-textposud,r"\textsf{(d)}",[text.halign.center,text.size.large])
# c.text(w0*1.67-txtposlr-0.4,h0*0.46-textposud,r"\textsf{(e)}",[text.halign.center,text.size.large])
# c.text(-txtposlr-0,h0*2-textposud-0.3,r"\textsf{(a)}",[text.halign.center,text.size.large])
# c.text(w0*1.4-txtposlr-0.2,h0*2-textposud-0.3,r"\textsf{(b)}",[text.halign.center,text.size.large])

c.writePDFfile('fig_template')
convert_from_path('fig_template.pdf',dpi=300)[0].save('fig_template.png')
print('='*60,'End!')



