#include <QToolBar>
#include <QIcon>
#include <QAction>
#include <QMenu>
#include <QMenuBar>
#include <QStatusBar>
#include <QTextEdit>
#include <QApplication>
#include <QErrorMessage>

#include "util/util.h"
#include "qutil/qutil.h"
#include "dlg/testdialog.h"
#include "appwindow.h"

void AppWindow::_showTestDialog()
{
    /*
    // modal dialog
    TestDialog dlg(this);
    dlg.exec();
    */

    // modeless dialog
    if(!_dlg) {
        _dlg = new TestDialog(this);
    }
    _dlg->show();
    _dlg->raise();
    _dlg->activateWindow();
}

AppWindow::AppWindow()
{
    const QIcon newIcon  = QIcon::fromTheme("document-new", QIcon(":/icons/new.png"));
    const QIcon openIcon = QIcon::fromTheme("document-open", QIcon(":/icons/open.png"));
    const QIcon quitIcon = QIcon::fromTheme("application-exit", QIcon(":/icons/quit.png"));
    const QIcon dlgIcon  = QIcon(":/icons/dialog.png");

    auto* newAct  = new QAction(newIcon, tr("&New"), this);
    auto* openAct = new QAction(openIcon, tr("&Open"), this);
    auto* dlgAct  = new QAction(dlgIcon, tr("&Test dialog"), this);
    auto* quitAct = new QAction(quitIcon, tr("&Quit"), this);
    quitAct->setShortcuts(QKeySequence::Quit);
    quitAct->setStatusTip(tr("Exit the application"));

    connect(quitAct, &QAction::triggered, qApp, &QApplication::quit);
    connect(dlgAct, &QAction::triggered, this, &AppWindow::_showTestDialog);

    auto* menu = menuBar()->addMenu(tr("&File"));
    menu->addAction(newAct);
    menu->addAction(openAct);
    menu->addAction(dlgAct);
    menu->addAction(quitAct);

    auto* toolbar = addToolBar(tr("Main toolbar"));
    toolbar->addAction(newAct);
    toolbar->addAction(openAct);
    toolbar->addAction(dlgAct);
    toolbar->addSeparator();
    toolbar->addAction(quitAct);

    auto* edit = new QTextEdit(this);
    edit->setText(tr("Hello, world!"));
    edit->append(QStringLiteral("Current locale: %1").arg(QLocale::system().name()));
    edit->append(QStringLiteral("Translated: '%1 %2'").arg(
                    QErrorMessage::tr("Debug Message:"), tr("Qt5 demo")));
    edit->append(QStringLiteral("Qt version: ") + qVersion());
    edit->append(QStringLiteral("3 + 4 = %1").arg(calcSum(3,4)));
    edit->append(QStringLiteral("Something calculated: %1").arg(calcSomething()));

    setCentralWidget(edit);

    statusBar()->showMessage(tr("Ready"));
}
