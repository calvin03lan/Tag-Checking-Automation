下面是新的URL读取和管理规则

# 读取和拼接
根据客户要求，Excel表格中的L列（URL path name）不能放完整的URL了，取而代之的是URL的其中一部分，具体需要通过下面的逻辑来识别、读取和拼凑：
1. URL有两种：pws和cms。区分他们的特点是，cms读入的字符串里一定会有“/cms”这几个字母，而pws没有
2. 如果读到的是pws，拼接的规则是：title + lang + URL path name
3. 如果读到的是cms，拼接的规则是：title + URL path name + lang + "/index.html"

## 关于title
title是URL的开头
1. pws URL的默认开头是：https://www.hangseng.com
2. cms URL的默认开头是：https://cms.hangseng.com
除此之外还有一些特殊情况，比如“https://uat-cms.hangseng.com”

## 关于lang
lang是语言选项，但是会有不同的形式
1. pws URL的默认语言形式是：/zh-hk /zh-cn /en-hk
2. cms URL的默认语言形式是：/chi /schi /eng
除此之外不排除还有其他情况
另外，原表格还会有一种语言选项是（All），这就是说要把对应的URL拼接为三种语言的网页，并且把Excel中只有一行的case分成三份，keywords窗格中也应该有对应的三种。
