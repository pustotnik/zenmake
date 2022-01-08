#include <QToolBar>
#include <QIcon>
#include <QAction>
#include <QMenu>
#include <QMenuBar>
#include <QStatusBar>
#include <QTextEdit>
#include <QApplication>

#include "appwindow.h"

AppWindow::AppWindow()
{
    auto* newAct = new QAction(tr("&New"), this);
    auto* openAct = new QAction(tr("&Open"), this);
    auto* quitAct = new QAction(tr("&Quit"), this);
    quitAct->setShortcuts(QKeySequence::Quit);
    quitAct->setStatusTip(tr("Exit the application"));

    connect(quitAct, &QAction::triggered, qApp, &QApplication::quit);

    auto* menu = menuBar()->addMenu(tr("&File"));
    menu->addAction(newAct);
    menu->addAction(openAct);
    menu->addAction(quitAct);

    auto* toolbar = addToolBar(tr("Main toolbar"));
    toolbar->addAction(newAct);
    toolbar->addAction(openAct);
    toolbar->addSeparator();
    toolbar->addAction(quitAct);

    auto* edit = new QTextEdit(this);
    edit->setText("Hello, world!");
    edit->append(QString("Qt version: ") + qVersion());

    setCentralWidget(edit);

    statusBar()->showMessage(tr("Ready"));
}
