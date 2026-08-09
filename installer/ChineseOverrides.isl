; DaFeiYu Desktop Pet - Simplified Chinese installer overrides.
; Default.isl is loaded before this file, so new Inno messages retain a safe
; English fallback instead of making the release build depend on a separately
; installed language pack.

[LangOptions]
LanguageName=简体中文
LanguageID=$0804
LanguageCodePage=936
DialogFontName=Microsoft YaHei UI
DialogFontSize=9
WelcomeFontName=Microsoft YaHei UI
WelcomeFontSize=13

[Messages]
SetupAppTitle=安装
SetupWindowTitle=%1 安装
UninstallAppTitle=卸载
UninstallAppFullTitle=%1 卸载
InformationTitle=信息
ConfirmTitle=确认
ErrorTitle=错误
SetupLdrStartupMessage=即将安装 %1，是否继续？
SetupAlreadyRunning=安装程序已经在运行。
WindowsVersionNotSupported=当前 Windows 版本不受支持。
OnlyOnTheseArchitectures=此程序只能安装到以下处理器架构的 Windows：%n%n%1
SetupAppRunningError=检测到 %1 正在运行。%n%n请关闭程序后点击“确定”继续，或点击“取消”退出。
UninstallAppRunningError=检测到 %1 正在运行。%n%n请关闭程序后点击“确定”继续，或点击“取消”退出。
ExitSetupTitle=退出安装
ExitSetupMessage=安装尚未完成。现在退出将不会安装程序。%n%n确定退出吗？
ButtonBack=< 上一步(&B)
ButtonNext=下一步(&N) >
ButtonInstall=安装(&I)
ButtonOK=确定
ButtonCancel=取消
ButtonYes=是(&Y)
ButtonNo=否(&N)
ButtonFinish=完成(&F)
ButtonBrowse=浏览(&B)...
ButtonWizardBrowse=浏览(&R)...
SelectLanguageTitle=选择安装语言
SelectLanguageLabel=请选择安装程序使用的语言。
ClickNext=点击“下一步”继续，或点击“取消”退出。
WelcomeLabel1=欢迎使用 [name] 安装向导
WelcomeLabel2=此向导将在您的电脑上安装 [name/ver]。%n%n继续之前，建议关闭其他应用程序。
WizardSelectDir=选择安装位置
SelectDirDesc=您想将 [name] 安装在哪里？
SelectDirLabel3=安装程序会将 [name] 安装到以下文件夹。
SelectDirBrowseLabel=点击“下一步”继续；如需更改文件夹，请点击“浏览”。
DiskSpaceGBLabel=至少需要 [gb] GB 可用空间。
DiskSpaceMBLabel=至少需要 [mb] MB 可用空间。
WizardSelectTasks=选择附加任务
SelectTasksDesc=安装时还需要完成哪些附加任务？
SelectTasksLabel2=选择需要的附加任务，然后点击“下一步”。
WizardReady=准备安装
ReadyLabel1=安装程序已准备好将 [name] 安装到您的电脑。
ReadyLabel2a=点击“安装”开始；如需修改设置，请点击“上一步”。
ReadyLabel2b=点击“安装”开始。
ReadyMemoDir=安装位置：
ReadyMemoTasks=附加任务：
WizardPreparing=正在准备安装
PreparingDesc=安装程序正在准备安装 [name]。
ApplicationsFound2=以下程序正在使用需要更新的文件。建议允许安装程序自动关闭它们，完成后会尝试重新启动。
CloseApplications=自动关闭应用程序(&A)
DontCloseApplications=不要关闭应用程序(&D)
WizardInstalling=正在安装
InstallingLabel=正在安装 [name]，请稍候。
FinishedHeadingLabel=[name] 安装完成
FinishedLabelNoIcons=[name] 已安装到您的电脑。
FinishedLabel=[name] 已安装完成，可通过快捷方式启动。
ClickFinish=点击“完成”退出安装程序。
RunEntryExec=运行 %1
StatusClosingApplications=正在关闭应用程序...
StatusCreateDirs=正在创建文件夹...
StatusExtractFiles=正在解压文件...
StatusCreateIcons=正在创建快捷方式...
StatusSavingUninstall=正在保存卸载信息...
StatusRunProgram=正在完成安装...
StatusRestartingApplications=正在重新启动应用程序...
ErrorExecutingProgram=无法运行文件：%n%1
ConfirmUninstall=确定要移除 %1 及其所有组件吗？
UninstallStatusLabel=正在从电脑中移除 %1，请稍候。
UninstalledAll=%1 已成功移除。
WizardUninstalling=卸载状态
StatusUninstalling=正在卸载 %1...

[CustomMessages]
AdditionalIcons=附加快捷方式：
CreateDesktopIcon=创建桌面快捷方式(&D)
LaunchProgram=运行 %1
UninstallProgram=卸载 %1
