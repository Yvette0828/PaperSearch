from PyQt6 import QtCore, QtGui, QtWidgets, uic
from PyQt6.QtWidgets import QMessageBox, QFileDialog
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDesktopServices, QPixmap
from PyQt6.QtCore import QUrl
import os
import sys
import math
import pandas as pd
import sqlite3
from sqlite3 import Error

class TableModel(QtCore.QAbstractTableModel):
 
    def __init__(self, data):
        super(TableModel, self).__init__()
        self._data = data
 
    def data(self, index, role):
        if role == Qt.ItemDataRole.DisplayRole:
            value = self._data.iloc[index.row(), index.column()] #pandas's iloc method
            return str(value)
 
        if role == Qt.ItemDataRole.TextAlignmentRole:          
            return Qt.AlignmentFlag.AlignVCenter + Qt.AlignmentFlag.AlignHCenter
         
        if role == Qt.ItemDataRole.BackgroundRole and (index.row()%2 == 0):
            return QtGui.QColor('#F0F8FF')
 
    def rowCount(self, index):
        return self._data.shape[0]
    
 
    def columnCount(self, index):
        return self._data.shape[1]
 
    # Add Row and Column header
    def headerData(self, section, orientation, role):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal and section < self._data.shape[1]:
                return str(self._data.columns[section])
            elif orientation == Qt.Orientation.Vertical and section < self._data.shape[0]:
                return str(self._data.index[section])
            else:
                return None

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        uic.loadUi('./PySQLite_HW.ui', self) # 加載UI文件
        self.show()
        database = './database.sqlite'
        # create a database connect
        self.conn = create_connection(database)
        self.setWindowTitle('Paper Query System')

    # Signals
        self.pushButton_exit.clicked.connect(self.showExitDialog)
        self.pushButton_exit_Tab2.clicked.connect(self.showExitDialog)
        self.pushButton_exit_Tab3.clicked.connect(self.showExitDialog)
        self.lineEdit_author.returnPressed.connect(self.searchByKeyword)
        self.lineEdit_keyword.returnPressed.connect(self.searchByKeyword)
        self.pushButton_search.clicked.connect(self.searchByKeyword)
        self.comboBox_eventType.setToolTip("Tip: You must select an event type to search.")
        self.comboBox_eventType.activated.connect(self.searchByKeyword)
        self.comboBox_page.activated.connect(self.showTable) # activated 是當選單有被點擊時才觸發
        self.pushButton_clearTable.clicked.connect(self.clearTable)
        self.pushButton_clearQuery.clicked.connect(self.clearQuery)
        self.tableView.doubleClicked.connect(self.rowSelected)
        self.pushButton_first.clicked.connect(self.firstPage)
        self.pushButton_last.clicked.connect(self.lastPage)
        self.pushButton_previous.clicked.connect(self.previousPage)
        self.pushButton_next.clicked.connect(self.nextPage)
        self.pushButton_backTab1.clicked.connect(self.goTab1)
        self.pushButton_paperSearch_Tab3.clicked.connect(self.goTab1)
        self.pushButton_goTab2.clicked.connect(self.goTab2)
        self.pushButton_FullContent_Tab3.clicked.connect(self.goTab2)
        self.pushButton_image_Tab1.clicked.connect(self.goTab3)
        self.pushButton_image_Tab2.clicked.connect(self.goTab3)
        self.pushButton_scholar.clicked.connect(self.GoogleScholar)
        self.pushButton_scholar_Tab2.clicked.connect(self.GoogleScholar)
        self.pushButton_save.clicked.connect(self.saveData) # 存成檔案

    # Slots
        
    def searchByKeyword(self):
        author_key = self.lineEdit_author.text()
        title_key = self.lineEdit_keyword.text()
        eventtype = str(self.comboBox_eventType.currentText())
        if eventtype == '':
            dlg = QMessageBox(self)
            dlg.setWindowTitle("Warning")
            dlg.setText("Please select the event type!")
            dlg.setStandardButtons(QMessageBox.StandardButton.Yes)
            buttonY = dlg.button(QMessageBox.StandardButton.Yes)
            buttonY.setText('OK')
            dlg.setIcon(QMessageBox.Icon.Information)
            button = dlg.exec()
            sql = ''
        elif eventtype == 'Poster, Oral, Spotlight':
            sql = f"SELECT DISTINCT A.id, C.name, A.title, A.eventtype, A.abstract, A.papertext, A.imgfile \
                FROM papers A, paperauthors B, authors C \
                WHERE C.name LIKE '%{author_key}%' AND B.authorid=C.id AND B.paperid=A.id AND A.title LIKE '%{title_key}%' \
                GROUP BY A.id"
        else:
            sql = f"SELECT DISTINCT A.id, C.name, A.title, A.eventtype, A.abstract, A.papertext, A.imgfile \
                FROM papers A, paperauthors B, authors C \
                WHERE C.name LIKE '%{author_key}%' AND B.authorid=C.id AND B.paperid=A.id AND A.title LIKE '%{title_key}%' AND A.eventtype='{eventtype}' \
                GROUP BY A.id"
        with self.conn:
            self.rows = SQLExecute(self, sql)
            if len(self.rows) > 0: 
                ToTableView(self, self.rows)

    def showTable(self):
        page = int(self.comboBox_page.currentText())
        start_idx = (page - 1) * 10
        end_idx = start_idx + 10
        data = self.df.iloc[start_idx:end_idx, :]
        self.model = TableModel(data)
        self.tableView.setModel(self.model)

    def clearTable(self):
        self.lineEdit_total.setText('')
        self.comboBox_page.clear()
        self.textBrowser_authors.setText('')
        self.textBrowser_title.setText('')
        self.textBrowser_abstract.setText('')
        self.textBrowser_fullContent.setText('')
        self.df = pd.DataFrame()
        self.model = TableModel(self.df)
        self.tableView.setModel(self.model)
    
    def clearQuery(self):
        self.lineEdit_author.setText('')
        self.lineEdit_keyword.setText('')
        self.comboBox_eventType.setCurrentIndex(-1)

    def rowSelected(self, mi):
        # print([mi.row(), mi.column()])
        if 'Abstract' in self.df.columns:
            col_list = list(self.df.columns)
        else:
            print('No Abstract from the Query')
            return
        # display Abstract on TextBrowser, then go fetch author names
        self.textBrowser_abstract.setText(self.df.iloc[mi.row(), col_list.index('Abstract')])
        self.textBrowser_title.setText(self.df.iloc[mi.row(), col_list.index('Title')])
        self.textBrowser_fullContent.setText(self.df.iloc[mi.row(), col_list.index('PaperText')])
        self.img_name = u"./NIP2015_Images/" + self.df.iloc[mi.row(), col_list.index('imgfile')]
        # print(self.img_name)
        self.label_image.setPixmap(QPixmap(self.img_name))
        show_authors(self, self.df.iloc[mi.row(), 0])
         # show the count of author(s)
        Title = str(self.df.iloc[mi.row(), col_list.index('Title')])
        sql = f"SELECT COUNT(AuthorId) FROM PaperAuthors WHERE PaperId = (SELECT Id FROM Papers WHERE Title = '{Title}')"
        with self.conn:
            author_count = SQLExecute(self, sql)
            for i in author_count:
                num = int(i[0])
        if num == 1:
            self.label_7.setText(f'Author: ({num} author)')
        else:
            self.label_7.setText(f'Authors: ({num} authors)')

    def GoogleScholar(self):
        title_text = self.textBrowser_title.toPlainText()
        if title_text == '':
            QMessageBox.warning(self, "Warning", "Please select the paper by double clicking the data in table!")
        else:
            search_url = f"https://scholar.google.com/scholar?hl=en&as_sdt=0%2C5&q={title_text}"
            QDesktopServices.openUrl(QUrl(search_url))

    def goTab1(self):
        self.tabWidget.setCurrentIndex(0)

    def goTab2(self):
        self.tabWidget.setCurrentIndex(1)

    def goTab3(self):
        self.tabWidget.setCurrentIndex(2)

    def firstPage(self):
            try:
                page = int(1)
                if self.comboBox_page.currentText() == str(page):
                    QMessageBox.warning(self, "Warning", "This is already the first page!")
                else:
                    self.comboBox_page.setCurrentText(str(page))
                    start_idx = (page - 1) * 10
                    end_idx = start_idx + 10
                    data = self.df.iloc[start_idx:end_idx, :]
                    self.model = TableModel(data)
                    self.tableView.setModel(self.model)
            except:
                QMessageBox.warning(self, "Warning", "No result!")

    def lastPage(self):
        try:
            page = int(self.comboBox_page.itemText(self.comboBox_page.count() - 1))
            if self.comboBox_page.currentText() == str(page):
                    QMessageBox.warning(self, "Warning", "This is already the last page!")
            else:
                self.comboBox_page.setCurrentText(str(page))
                start_idx = (page - 1) * 10
                end_idx = start_idx + 10
                data = self.df.iloc[start_idx:end_idx, :]
                self.model = TableModel(data)
                self.tableView.setModel(self.model)
        except:
            QMessageBox.warning(self, "Warning", "No result!")
        
    def previousPage(self):
        try:
            page = int(self.comboBox_page.currentText())
            first_page = int(1)
            if page == first_page:
                QMessageBox.warning(self, "Warning", "This is already the first page!")
            else:
                start_idx = (page - 2) * 10
                end_idx = start_idx + 10
                data = self.df.iloc[start_idx:end_idx, :]
                self.model = TableModel(data)
                self.tableView.setModel(self.model)
                page = self.comboBox_page.setCurrentText(str(int(self.comboBox_page.currentText())-1))
        except:
            QMessageBox.warning(self, "Warning", "No result!")

    def nextPage(self):
        try:
            page = int(self.comboBox_page.currentText())
            last_page = int(self.comboBox_page.itemText(self.comboBox_page.count() - 1))
            if page == last_page:
                QMessageBox.warning(self, "Warning", "This is already the last page!") 
            else:
                start_idx = (page) * 10
                end_idx = start_idx + 10
                data = self.df.iloc[start_idx:end_idx, :]
                self.model = TableModel(data)
                self.tableView.setModel(self.model)
                page = self.comboBox_page.setCurrentText(str(int(self.comboBox_page.currentText())+1))
        except: 
            QMessageBox.warning(self, "Warning", "No result!")
        
    def saveData(self):
        fname, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Save file', 
            "", "EXCEL files (*.xlsx)") #儲存名稱可預設成 pdfName in database
        if len(fname) != 0:
            self.df.to_excel(fname)

    def showExitDialog(self):
        # 顯示確認視窗
        choice = QMessageBox.question(self, 'Exit Dialog', 'Are you sure to exit')
        # 如果點選 Yes，則關閉 app
        if choice == QMessageBox.StandardButton.Yes:
            self.conn.close() # close database
            self.close() # close app

def create_connection(db_file):
    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except Error as e:
        print(e)
 
    return conn

def SQLExecute(self, SQL):
    self.cur = self.conn.cursor()
    self.cur.execute(SQL)
    rows = self.cur.fetchall()

    if len(rows) == 0 and SQL != '': # nothing found
        # raise a messageBox here
        dlg = QMessageBox(self)
        dlg.setWindowTitle("SQL Information: ")
        dlg.setText("No data match the query!")
        dlg.setStandardButtons(QMessageBox.StandardButton.Yes)
        buttonY = dlg.button(QMessageBox.StandardButton.Yes)
        buttonY.setText('OK')
        dlg.setIcon(QMessageBox.Icon.Information)
        button = dlg.exec()
        # return
    return rows

def ToTableView(self, rows):
    self.comboBox_page.clear()
    names = [description[0] for description in self.cur.description] # extract column names
    self.df = pd.DataFrame(rows)
    self.model = TableModel(self.df)
    self.tableView.setModel(self.model)
    self.df.columns = names
    self.df.index = range(1, len(rows)+1)
    self.lineEdit_total.setText(str(len(rows)))
    self.comboBox_page.addItems(list(map(str, range(1, math.ceil(len(rows)/10)+1))))

    page = 0
    start_idx = (page) * 10
    end_idx = start_idx + 10
    data = self.df.iloc[start_idx:end_idx, :]
    self.model = TableModel(data)
    self.tableView.setModel(self.model)

def show_authors(self, paperid):
    sql = "select name from authors A, paperauthors B where B.paperid="+str(paperid)+" and A.id=B.authorid"
    with self.conn:
        self.rows = SQLExecute(self, sql)
        names =""
        for row in self.rows:
            names = names + row[0] +"; "
        self.textBrowser_authors.setText(names)

def exit():
    app = QtWidgets.QApplication(sys.argv)
    sys.exit(app.exec())

def fetch_paperid(conn):
    cur = conn.cursor()
    sql = "select id from papers"
    cur.execute(sql)
    rows = cur.fetchall()
    return rows
     
def update_papers(conn, params):
     
    sql = "UPDATE papers set imgfile = ? WHERE id = ?"
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()

def main():
    database = './database.sqlite' # 建立與數據庫的連接
    file_src = './NIP2015_Images/'
    picName = os.listdir(file_src)
    # print(picName)
    conn = create_connection(database)
    # fetch paper id
    paperid = fetch_paperid(conn)
    with conn:
        for i in range(len(paperid)):
            update_papers(conn, (picName[i], paperid[i][0]))
    conn.close()
    app = QtWidgets.QApplication(sys.argv)
    main = MainWindow()
    main.show()
    sys.exit(app.exec())
 
if __name__ == '__main__':
    main()