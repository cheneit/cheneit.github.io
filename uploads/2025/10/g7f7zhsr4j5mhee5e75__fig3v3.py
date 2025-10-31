import os
import numpy as np
import scipy.io as io
from pyx import *
from pdf2image import convert_from_path

text.set(text.LatexEngine,texenc='utf-8')

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

parula = color.functiongradient_rgb(
    f_r = lambda x:  -21.4*(1-x)**4 + 40.7*(1-x)**3 - 22.1*(1-x)**2 + 3.46*(1-x) + 0.13,
    f_g = lambda x: 7.885*(1-x)**4 - 14.36*(1-x)**3 + 7.091*(1-x)**2 + 0.2187*(1-x) + 0.15,
    f_b = lambda x: 0.02211*(1-x)**4 +5.409*(1-x)**3 -9.264*(1-x)**2 + 3.35*(1-x) + 0.63)

bwr = color.functiongradient_rgb(
    f_r=lambda x:  4.9*(1-x)**4 - 10*(1-x)**3 + 4.9*(1-x)**2 - 0.58*(1-x) + 0.9,
    f_g = lambda x: 13*(1-x)**4 - 26*(1-x)**3 + 13*(1-x)**2 - 0.15*(1-x) + 0.2,
    f_b = lambda x: 6.4*(1-x)**4 - 13*(1-x)**3 + 6.3*(1-x)**2 + 0.99*(1-x) + 0.054)
    
bwr_darker = color.functiongradient_rgb(
    f_r=lambda x:  7.308*(1-x)**4 -12.22*(1-x)**3 +2.899*(1-x)**2 + 1.585*(1-x) + 0.4755,
    f_g = lambda x: 10.15*(1-x)**4 - 20.81*(1-x)**3 + 10.36*(1-x)**2 + 0.5829*(1-x) + 0.05,
    f_b = lambda x: 9.461*(1-x)**4 -21.49*(1-x)**3 +13.52*(1-x)**2 - 1.132*(1-x) + 0.1528)
#-----------------------------------------------------#
# LOAD DATA
#-----------------------------------------------------#
print('='*60,'Plotting Figure')
print('-'*40,'Load data')

xsa,ysa0,ysa1,ysa2 = io.loadmat('amqsh_100_G.mat')['xs'][0],io.loadmat('amqsh_100_G.mat')['gsu'][0],io.loadmat('amqsh_100_G.mat')['gsd'][0],io.loadmat('amqsh_100_G.mat')['gs'][0]

xsb,ysb0,ysb1,ysb2 = io.loadmat('amqah_100_G.mat')['xs'][0],io.loadmat('amqah_100_G.mat')['gsu'][0],io.loadmat('amqah_100_G.mat')['gsd'][0],io.loadmat('amqah_100_G.mat')['gs'][0]

xsc0,ysc0 = io.loadmat('amqsh_mag_anderson_disorder.mat')['ws'][0],io.loadmat('amqsh_mag_anderson_disorder.mat')['Gs'][0]
xsc1,ysc1 = io.loadmat('amqsh_nonmag_anderson_disorder.mat')['ws'][0],io.loadmat('amqsh_nonmag_anderson_disorder.mat')['Gs'][0]
xsc2,ysc2 = io.loadmat('amqsh_mag_longrange_disorder.mat')['ws'][0],io.loadmat('amqsh_mag_longrange_disorder.mat')['Gs'][0]
xsc3,ysc3 = io.loadmat('amqsh_nonmag_longrange_disorder.mat')['ws'][0],io.loadmat('amqsh_nonmag_longrange_disorder.mat')['Gs'][0]

xsd0,ysd0 = io.loadmat('amqah_mag_anderson_disorder.mat')['ws'][0],io.loadmat('amqah_mag_anderson_disorder.mat')['Gs'][0]
xsd1,ysd1 = io.loadmat('amqah_nonmag_anderson_disorder.mat')['ws'][0],io.loadmat('amqah_nonmag_anderson_disorder.mat')['Gs'][0]
xsd2,ysd2 = io.loadmat('amqah_mag_longrange_disorder.mat')['ws'][0],io.loadmat('amqah_mag_longrange_disorder.mat')['Gs'][0]
xsd3,ysd3 = io.loadmat('amqah_nonmag_longrange_disorder.mat')['ws'][0],io.loadmat('amqah_nonmag_longrange_disorder.mat')['Gs'][0]

jl_data0 = io.loadmat('amqsh_100_jl_data.mat')
lx0,ly0,lz0,jx0,jy0,angle0,size0 = jl_data0['lx'][0],jl_data0['ly'][0],jl_data0['lz'][0],jl_data0['jx'][0],jl_data0['jy'][0],jl_data0['angle'][0],jl_data0['size'][0]

lx0,ly0,jx0,jy0 = [lx0i/1/1e9 for lx0i in lx0],[ly0i/1/1e9 for ly0i in ly0],[jx0i/1/1e9 for jx0i in jx0],[jy0i/1/1e9 for jy0i in jy0]

jl_data1 = io.loadmat('amqah_100_jl_data.mat')
lx1,ly1,lz1,jx1,jy1,angle1,size1 = jl_data1['lx'][0],jl_data1['ly'][0],jl_data1['lz'][0],jl_data1['jx'][0],jl_data1['jy'][0],jl_data1['angle'][0],jl_data1['size'][0]

lx1,ly1,jx1,jy1 = [lx1i/1/1e9 for lx1i in lx1],[ly1i/1/1e9 for ly1i in ly1],[jx1i/1/1e9 for jx1i in jx1],[jy1i/1/1e9 for jy1i in jy1]
#----------------------------------------------------#
print('-'*40,'Figures setting')
w0 = 4.2
h0 = 2.5

hef = 2.0
wef = hef*(max(lx0)-min(lx0))/(max(ly0)-min(ly0))

wspace = 0.8
hspace = 1

xlabel_a = r'$E_F$ (meV)'
ylabel_a = r'$G\,(e^2/h)$'

xlabel_b = r'$E_F$ (meV)'
ylabel_b = r'$G\,(e^2/h)$'

xmin_a,xmax_a = -0.5,0.5
ymin_a,ymax_a = 0,2.2

xmin_b,xmax_b = -0.5,0.5
ymin_b,ymax_b = 0,2.2

xlabel_c = r'$W$ (meV)'
ylabel_c = r'$G\,(e^2/h)$'

xlabel_d = r'$W$ (meV)'
ylabel_d = r'$G\,(e^2/h)$'

xmin_c,xmax_c = 0,1
ymin_c,ymax_c = 0,2.2

xmin_d,xmax_d = 0,1
ymin_d,ymax_d = 0,2.2

#-------------------------------
# a/ b/ 
#-------------------------------
c = canvas.canvas()
mypainter_xall = graph.axis.painter.regular(titledist=0.1*unit.v_cm,titlepos=0.5,labeldist=0.1*unit.v_cm)
mypainter_yall = graph.axis.painter.regular(titledist=0.1*unit.v_cm,titlepos=0.5,labeldist=0.1*unit.v_cm)

myticksx = [graph.axis.tick.tick(-30,label=r'$-$50'),graph.axis.tick.tick(0,label=''),\
            graph.axis.tick.tick(30,label=r'50')]

ga = c.insert(graph.graphxy(width=w0,height=h0,ypos=2*h0+2*hspace,
		x = graph.axis.linear(min=xmin_a,max=xmax_a,title=xlabel_a,density=0.5,painter=mypainter_xall),
                   y = graph.axis.linear(min=ymin_a,max=ymax_a,title=ylabel_a,density=0.5,painter=mypainter_yall),
                   key = graph.key.key(pos=None,hpos=0.,vpos=1.,symbolspace=0.05*unit.v_cm,
                            symbolwidth = 0.5*unit.v_cm,dist=0.15*unit.v_cm,textattrs=[text.size.small])))

gb = c.insert(graph.graphxy(width=w0,height=h0,xpos=w0+wspace,ypos=2*h0+2*hspace,
		x = graph.axis.linear(min=xmin_a,max=xmax_a,title=xlabel_a,density=0.5,painter=mypainter_xall),
                   y = graph.axis.linkedaxis(ga.axes["y"]),))

gc = c.insert(graph.graphxy(width=w0,height=h0,
		x = graph.axis.linear(min=xmin_c,max=xmax_c,title=xlabel_c,density=0.5,painter=mypainter_xall),
                   y = graph.axis.linear(min=ymin_c,max=ymax_c,title=ylabel_c,density=0.5,painter=mypainter_yall),
                   key = graph.key.key(pos=None,hpos=0.,vpos=0,symbolspace=0.05*unit.v_cm,
                            symbolwidth = 0.5*unit.v_cm,dist=0.15*unit.v_cm,textattrs=[text.size.small]),))

gd = c.insert(graph.graphxy(width=w0,height=h0,xpos=w0+wspace,
		x = graph.axis.linear(min=xmin_d,max=xmax_d,title=xlabel_d,density=0.5,painter=mypainter_xall),
                   y = graph.axis.linkedaxis(gc.axes["y"]),
                            ))
                            
ge = c.insert(graph.graphxy(width=wef,height=hef,ypos=h0+hspace,
		x = graph.axis.linear(min=-30,max=30,title=r'$x/a_0$',manualticks=myticksx,density=0.25,painter=graph.axis.painter.regular(titledist=-0.2*unit.v_cm,titlepos=0.5,labeldist=0.1*unit.v_cm),
		parter=graph.axis.parter.linear(['30','15'])),
		y = graph.axis.linear(min=min(ly0),max=max(ly0),title=r'$y/a_0$',density=0.5,painter=graph.axis.painter.regular(titledist=-0.2*unit.v_cm,titlepos=0.5,labeldist=0.1*unit.v_cm),
		parter=graph.axis.parter.linear(['25','12.5'])),
		))
gf = c.insert(graph.graphxy(width=wef,height=hef,xpos=w0+wspace-0.5,ypos=h0+hspace,
		x = graph.axis.linear(min=-30,max=30,title=r'$x/a_0$',manualticks=myticksx,density=0.25,painter=graph.axis.painter.regular(titledist=-0.2*unit.v_cm,titlepos=0.5,labeldist=0.1*unit.v_cm),
		parter=graph.axis.parter.linear(['30','15'])),
		y =  graph.axis.linkedaxis(ge.axes["y"]),
		))


colors0 = [color.cmyk.Violet,color.cmyk.Violet,color.cmyk.Green,color.cmyk.Green]
samplesize = 0.12*unit.v_cm

ga.plot(graph.data.values(x=xsa[::2],y=ysa0[::2],title=r'$G_{\uparrow}$'),
	styles=[graph.style.line(lineattrs=[color.cmyk.RedOrange,style.linewidth.Thick,style.linestyle.solid]),
	graph.style.symbol(symbol=graph.style.symbol.square,size=samplesize,symbolattrs=[color.cmyk.RedOrange,deco.filled])])
ga.plot(graph.data.values(x=xsa[::2],y=ysa1[::2],title=r'$G_{\downarrow}$'),
	styles=[graph.style.line(lineattrs=[color.cmyk.RoyalBlue,style.linewidth.Thick,style.linestyle.solid]),
	graph.style.symbol(symbol=graph.style.symbol.square,size=samplesize,symbolattrs=[color.cmyk.RoyalBlue,deco.filled])])

gb.plot(graph.data.values(x=xsb[::2],y=ysb0[::2],title=r'$G_{\uparrow}$'),
	styles=[graph.style.line(lineattrs=[color.cmyk.RedOrange,style.linewidth.Thick,style.linestyle.solid]),
	graph.style.symbol(symbol=graph.style.symbol.square,size=samplesize,symbolattrs=[color.cmyk.RedOrange,deco.filled])])
gb.plot(graph.data.values(x=xsb[::2],y=ysb1[::2],title=r'$G_{\downarrow}$'),
	styles=[graph.style.line(lineattrs=[color.cmyk.RoyalBlue,style.linewidth.Thick,style.linestyle.solid]),
	graph.style.symbol(symbol=graph.style.symbol.square,size=samplesize,symbolattrs=[color.cmyk.RoyalBlue,deco.filled])])
           
gc.plot(graph.data.values(x=xsc0,y=ysc0,title='MA'),styles=[graph.style.line(lineattrs=[colors0[0],style.linewidth.Thick,style.linestyle.solid]),
        graph.style.symbol(symbol=graph.style.symbol.triangle,size=samplesize,symbolattrs=[colors0[0],deco.filled])])
gc.plot(graph.data.values(x=xsc1,y=ysc1,title='NMA'),styles=[graph.style.line(lineattrs=[colors0[1],style.linewidth.Thick,style.linestyle.solid]),
        graph.style.symbol(symbol=graph.style.symbol.square,size=samplesize,symbolattrs=[colors0[1],deco.filled])])
gc.plot(graph.data.values(x=xsc2,y=ysc2,title='ML'),styles=[graph.style.line(lineattrs=[colors0[2],style.linewidth.Thick,style.linestyle.solid]),
        graph.style.symbol(symbol=graph.style.symbol.diamond,size=samplesize,symbolattrs=[colors0[2],deco.filled])])
gc.plot(graph.data.values(x=xsc3,y=ysc3,title='NML'),styles=[graph.style.line(lineattrs=[colors0[3],style.linewidth.Thick,style.linestyle.solid]),
        graph.style.symbol(symbol=graph.style.symbol.circle,size=samplesize,symbolattrs=[colors0[3],deco.filled])])        

gd.plot(graph.data.values(x=xsd0,y=ysd0,title='MA'),styles=[graph.style.line(lineattrs=[colors0[0],style.linewidth.Thick,style.linestyle.solid]),
        graph.style.symbol(symbol=graph.style.symbol.triangle,size=samplesize,symbolattrs=[colors0[0],deco.filled])])
gd.plot(graph.data.values(x=xsd1,y=ysd1,title='NMA'),styles=[graph.style.line(lineattrs=[colors0[1],style.linewidth.Thick,style.linestyle.solid]),
        graph.style.symbol(symbol=graph.style.symbol.square,size=samplesize,symbolattrs=[colors0[1],deco.filled])])
gd.plot(graph.data.values(x=xsd2,y=ysd2,title='ML'),styles=[graph.style.line(lineattrs=[colors0[2],style.linewidth.Thick,style.linestyle.solid]),
        graph.style.symbol(symbol=graph.style.symbol.diamond,size=samplesize,symbolattrs=[colors0[2],deco.filled])])
gd.plot(graph.data.values(x=xsd3,y=ysd3,title='NML'),styles=[graph.style.line(lineattrs=[colors0[3],style.linewidth.Thick,style.linestyle.solid]),
        graph.style.symbol(symbol=graph.style.symbol.circle,size=samplesize,symbolattrs=[colors0[3],deco.filled])])  

gd.plot(graph.data.function('x(y)=0.75',min=0,max=2.2,title=None),
         styles=[graph.style.line(lineattrs=[color.cmyk.Gray,style.linewidth.Thick,style.linestyle.dashed])])


kge = graph.graphx(xpos=2*w0+wspace-0.5,ypos=h0+hspace,size=0.2,length=hef,direction='vertical',
		x=graph.axis.linear(min=0,max=1,title=r'$\rho_{\varepsilon}$',density=0.5,painter=graph.axis.painter.regular(titledist=-0.1*unit.v_cm,titlepos=0.5,labeldist=0.1*unit.v_cm)))
kgf = graph.graphx(xpos=2*w0+wspace+0.2,ypos=h0+hspace,size=0.3,length=h0,direction='vertical',
		x=graph.axis.linear(min=0,max=0.8,title=r'$\rho_{\varepsilon}$'))

ge.plot(graph.data.values(x=lx0,y=ly0,color=lz0),[graph.style.density(gradient=bwr_darker,keygraph=kge)])
ge.plot(graph.data.values(x=jx0,y=jy0,size=size0,angle=angle0),[graph.style.arrow(linelength=0.2*unit.v_cm,arrowsize=0.12*unit.v_cm,arrowpos=0.0,lineattrs=[color.cmyk.Blue])])

gf.plot(graph.data.values(x=lx1,y=ly1,color=lz1),[graph.style.density(gradient=bwr_darker,keygraph=kgf)])
gf.plot(graph.data.values(x=jx1,y=jy1,size=size1,angle=angle1),[graph.style.arrow(linelength=0.6*unit.v_cm,arrowsize=0.4*unit.v_cm,arrowpos=0.0,lineattrs=[color.cmyk.Blue])])

txtposlr,textposud = w0*0.1,h0*0.1

c.text(-txtposlr-0.2,3*h0+2*hspace-textposud,r"(a)",[text.halign.center,text.size.large])
c.text(w0+wspace-txtposlr,3*h0+2*hspace-textposud,r"(b)",[text.halign.center,text.size.large]) 
c.text(-txtposlr-0.2,2*h0+hspace-textposud,r"(c)",[text.halign.center,text.size.large])
c.text(w0+wspace-txtposlr,2*h0+hspace-textposud,r"(d)",[text.halign.center,text.size.large])
c.text(-txtposlr-0.2,h0-textposud,r"(e)",[text.halign.center,text.size.large])
c.text(w0+wspace-txtposlr,h0-textposud,r"(f)",[text.halign.center,text.size.large])

c.insert(kge)
c.writePDFfile('fig3')
convert_from_path('fig3.pdf',dpi=300)[0].save('fig3.png')
print('='*60,'End!')  
        
        
        
