# -*- coding: utf-8 -*-
# I need a class.
class D:
    def getAt1(self):
        return '''
<p>Notifia</p>
<ol>
  <li>Een</li>
  <li>Een</li>
  <li>Een</li>
  <li class="podItemKeepWithNext">Keep with next, without style mapping.</li>
  <li>Een</li>
  <li>Een</li>
  <li>Een</li>
  <li>Een</li>
  <li>Een</li>
  <li>Een</li>
  <li>Een</li>
  <ul><li class="pmItemKeepWithNext">This one has 'keep with next'</li>
        <li>Hello</li>
          <ol><li>aaaaaaaaaa aaaaaaaaaaaaaa</li>
              <li>aaaaaaaaaa aaaaaaaaaaaaaa</li>
              <li>aaaaaaaaaa aaaaaaaaaaaaaa</li>
              <li class="pmItemKeepWithNext">This one has 'keep with next'</li>
          </ol>
  </ul>
  <li>Een</li>
  <li>Een</li>
  <li>Een</li>
  <li>Een</li>
  <li>Een</li>
  <li>Een</li>
  <li class="pmItemKeepWithNext">This one has 'keep with next'</li>
</ol>
<ul>
  <li>Un</li>
  <li>Deux</li>
  <li>Trois</li>
  <li>Quatre</li>
  <li class="pmItemKeepWithNext">VCinq (this one has 'keep with next')</li>
  <li class="pmItemKeepWithNext">Six (this one has 'keep with next')</li>
  <li class="pmItemKeepWithNext">Sept (this one has 'keep with next')</li>
</ul>'''
dummy = D()

xhtml1 = '''
<p>First line</p>
<p>Second line: must be keepWithNext</p>
'''

xhtml2 = '''
<p>First line</p>
<ul>
 <li>1</li>
 <li>2</li>
 <li>This should be KWN</li>
</ul>
'''

xhtml3 = '''
<p>First line</p>
<ol>
 <li>This NB should be KWN</li>
</ol>
'''

# "Keep with next" with the ParaKWN class explicitly used
xhtml4 = '''
<p>First para</p>
<p class="ParaKWN">Hello1</p>
<p class="ParaKWN" style="text-align:justify">
 <span style="font-size:10.0pt">Hello.</span></p>
'''

# Idem, case #2
xhtml5 = '''
<p>TEST KWN #2</p>
<p style="text-align:justify">This line generates a style that must not be reused</p>
<p class="ParaKWN" style="text-align:justify">KWN</p>
'''
