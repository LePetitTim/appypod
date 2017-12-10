# ~license~
# ------------------------------------------------------------------------------
import os, os.path, sys, zipfile, re, shutil, six
from appy.shared.test import Tester, TestFactory, TesterError
from appy.shared.test import Test as BaseTest
from appy.shared.utils import FolderDeleter
from appy.shared.xml_parser import escapeXml
from appy.pod.odf_parser import OdfEnvironment, OdfParser
from appy.pod.renderer import Renderer
from appy.pod.styles_manager import \
     TableProperties, BulletedProperties, NumberedProperties

# TesterError-related constants ------------------------------------------------
TEMPLATE_NOT_FOUND = 'Template file "%s" was not found.'
CONTEXT_NOT_FOUND = 'Context file "%s" was not found.'
EXPECTED_RESULT_NOT_FOUND = 'Expected result "%s" was not found.'

# ------------------------------------------------------------------------------
def sjoin(folder, name):
    '''Shorthand for os.path.joining unicode strings.'''
    return str(os.path.join(folder, name))

# ------------------------------------------------------------------------------
class AnnotationsRemover(OdfParser):
    '''This parser is used to remove from content.xml and styles.xml the
       Python tracebacks that may be dumped into OpenDocument annotations by
       pod when generating errors. Indeed, those tracebacks contain lot of
       machine-specific info, like absolute paths to the python files, etc.'''
    def __init__(self, env, caller):
        OdfParser.__init__(self, env, caller)
        self.res = u''
        self.inAnnotation = False # Are we parsing an annotation ?
        self.textEncountered = False # Within an annotation, have we already
        # met a text ?
        self.ignore = False # Must we avoid dumping the current tag/content
        # into the result ?

    def startElement(self, elem, attrs):
        e = OdfParser.startElement(self, elem, attrs)
        # Do we enter into an annotation ?
        if elem == '%s:annotation' % e.ns(e.NS_OFFICE):
            self.inAnnotation = True
            self.textEncountered = False
        elif elem == '%s:p' % e.ns(e.NS_TEXT):
            if self.inAnnotation:
                if not self.textEncountered:
                    self.textEncountered = True
                else:
                    self.ignore = True
        if not self.ignore:
            self.res += '<%s' % elem
            for attrName, attrValue in attrs.items():
                self.res += ' %s="%s"' % \
                            (attrName, escapeXml(attrValue, escapeApos=True))
            self.res += '>'

    def endElement(self, elem):
        e = self.env
        if elem == '%s:annotation' % e.ns(e.NS_OFFICE):
            self.inAnnotation = False
            self.ignore = False
        if not self.ignore:
            self.res += '</%s>' % elem
        OdfParser.endElement(self, elem)

    def characters(self, content):
        e = OdfParser.characters(self, content)
        if not self.ignore: self.res += escapeXml(content)

    def getResult(self):
        return self.res

# ------------------------------------------------------------------------------
class Test(BaseTest):
    '''Abstract test class'''
    interestingOdtContent = ('content.xml', 'styles.xml')
    # "list-style"s can be generated in random order
    ignoreTags = ((OdfEnvironment.NS_DC, 'date'),
                  (OdfEnvironment.NS_STYLE, 'style'),
                  (OdfEnvironment.NS_TEXT, 'list-style'))
    # 'text:style-name's can contained generated names base on time.time
    ignoreAttrs = ('draw:name', 'text:name', 'text:bullet-char',
              'table:name', 'table:style-name', 'text:style-name', 'xlink:href')

    def __init__(self, testData, testDescription, testFolder,
                 config, flavour, rendererParams):
        BaseTest.__init__(self, testData, testDescription, testFolder, config,
                          flavour, rendererParams)
        self.templatesFolder = os.path.join(self.testFolder, 'templates')
        self.contextsFolder = os.path.join(self.testFolder, 'contexts')
        self.resultsFolder = os.path.join(self.testFolder, 'results')
        self.result = None
        self.rendererParams = rendererParams

    def getContext(self, contextName):
        '''Gets the objects that are in the context'''
        contextPy = os.path.join(self.contextsFolder, contextName + '.py')
        if not os.path.exists(contextPy):
            raise TesterError(CONTEXT_NOT_FOUND % contextPy)
        contextPkg = 'appy.pod.test.contexts.%s' % contextName
        six.exec_('import %s' % contextPkg)
        six.exec_('context = dir(%s)' % contextPkg)
        res = {}
        for elem in context:
            if not elem.startswith('__'):
                six.exec_('res[elem] = %s.%s' % (contextPkg, elem))
        return res

    def do(self):
        tempFileName = '%s.%s' % (self.data['Name'], self.data['Result'])
        self.result = sjoin(self.tempFolder, tempFileName)
        # Get the path to the template to use for this test
        if self.data['Template'].endswith('.ods'):
            suffix = ''
        else:
            # For ODT, which is the most frequent case, no need to specify the
            # file extension.
            suffix = '.odt'
        template = sjoin(self.templatesFolder, self.data['Template'] + suffix)
        if not os.path.exists(template):
            raise TesterError(TEMPLATE_NOT_FOUND % template)
        # Get the context
        context = self.getContext(self.data['Context'])
        # Get the LibreOffice port
        ooPort = self.data['LibreOfficePort']
        pythonWithUno = self.config['pythonWithUnoPath']
        # Get the styles mapping. Dicts are not yet managed by the TablesParser
        stylesMapping = eval('{' + self.data['StylesMapping'] + '}')
        # Call the renderer
        params = {'ooPort': ooPort, 'pythonWithUnoPath': pythonWithUno,
                  'stylesMapping': stylesMapping}
        params.update(self.rendererParams)
        Renderer(template, context, self.result, **params).run()

    def getOdtContent(self, odtFile):
        '''Creates in the temp folder content.xml and styles.xml extracted
           from p_odtFile.'''
        contentXml = None
        stylesXml = None
        if odtFile == self.result:
            filePrefix = 'actual'
        else:
            filePrefix = 'expected'
        zipFile = zipfile.ZipFile(odtFile)
        for zippedFile in zipFile.namelist():
            if zippedFile in self.interestingOdtContent:
                f = open(os.path.join(self.tempFolder,
                                      '%s.%s' % (filePrefix, zippedFile)), 'wb')
                fileContent = zipFile.read(zippedFile)
                if zippedFile in ('content.xml', 'styles.xml'):
                    # Python tracebacks that are in annotations include the full
                    # path to the Python files, which of course may be different
                    # from one machine to the other. So we remove those paths.
                    annotationsRemover = AnnotationsRemover(
                       OdfEnvironment(), self)
                    annotationsRemover.parse(fileContent)
                    fileContent = annotationsRemover.getResult()
                try:
                    f.write(fileContent.encode('utf-8'))
                except UnicodeDecodeError:
                    f.write(fileContent)
                f.close()
        zipFile.close()

    def checkResult(self):
        '''r_ is False if the test succeeded'''
        # Get styles.xml and content.xml from the actual result
        res = False
        self.getOdtContent(self.result)
        # Get styles.xml and content.xml from the expected result
        expectedResult = os.path.join(self.resultsFolder,
                                  self.data['Name'] + '.' + self.data['Result'])
        if not os.path.exists(expectedResult):
            raise TesterError(EXPECTED_RESULT_NOT_FOUND % expectedResult)
        self.getOdtContent(expectedResult)
        for fileName in self.interestingOdtContent:
            diffOccurred = self.compareFiles(
                os.path.join(self.tempFolder, 'actual.%s' % fileName),
                os.path.join(self.tempFolder, 'expected.%s' % fileName),
                areXml=True, xmlTagsToIgnore=Test.ignoreTags,
                xmlAttrsToIgnore=Test.ignoreAttrs, encoding='utf-8')
            if diffOccurred:
                res = True
                break
        return res

# Concrete test classes --------------------------------------------------------
class NominalTest(Test): pass
class ErrorTest(Test):
    def onError(self):
        '''Compares the error that occurred with the expected error'''
        Test.onError(self)
        return not self.isExpectedError(self.data['Message'])

# ------------------------------------------------------------------------------
class PodTestFactory(TestFactory):
    @staticmethod
    def createTest(testData, testDescription, testFolder, config, flavour,
                   rendererParams):
        isErrorTest = testData.table.instanceOf('ErrorTest')
        testClass = isErrorTest and ErrorTest or NominalTest
        return testClass(testData, testDescription, testFolder,
                         config, flavour, rendererParams)

# ------------------------------------------------------------------------------
class PodTester(Tester):
    def __init__(self, testPlan):
        Tester.__init__(self, testPlan, [], PodTestFactory)

# ------------------------------------------------------------------------------
if __name__ == '__main__': PodTester('Tests.odt').run()
# ------------------------------------------------------------------------------
