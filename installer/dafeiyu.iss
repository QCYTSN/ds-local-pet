#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef SourceDir
  #error SourceDir must point to the verified onedir release bundle.
#endif
#ifndef OutputDir
  #define OutputDir "."
#endif
#ifndef ExeName
  #define ExeName "DS-Local-Pet.exe"
#endif

#define AppName "大肥鱼桌宠"
#define AppNameEn "DaFeiYu Desktop Pet"
#define Publisher "QCYTSN"
#define ProjectUrl "https://github.com/QCYTSN/ds-local-pet"
#define InstalledExeName "DaFeiYuDesktopPet.exe"

[Setup]
AppId={{F5FCD73D-3299-4E46-A010-4F0C75F04E3E}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} v{#AppVersion}
AppPublisher={#Publisher}
AppPublisherURL={#ProjectUrl}
AppSupportURL={#ProjectUrl}/issues
AppUpdatesURL={#ProjectUrl}/releases
VersionInfoVersion={#AppVersion}.0
VersionInfoCompany={#Publisher}
VersionInfoDescription={#AppNameEn} installer
VersionInfoProductName={#AppNameEn}
VersionInfoProductVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\DaFeiYuDesktopPet
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir={#OutputDir}
OutputBaseFilename=DS-Local-Pet-Setup-v{#AppVersion}
SetupIconFile=..\icon.ico
UninstallDisplayIcon={app}\{#InstalledExeName}
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
WizardStyle=modern
Compression=lzma2/ultra64
SolidCompression=yes
CloseApplications=yes
RestartApplications=yes
SetupLogging=yes
UsePreviousAppDir=yes
UsePreviousTasks=yes
AllowNoIcons=yes

[Languages]
; Load Inno's complete built-in message set first, then override the visible
; installer flow in Chinese.  This is reproducible even when a machine does
; not have an optional language pack installed.
Name: "chinesesimp"; MessagesFile: "compiler:Default.isl,ChineseOverrides.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加快捷方式："; Flags: unchecked

[Files]
Source: "{#SourceDir}\{#ExeName}"; DestDir: "{app}"; DestName: "{#InstalledExeName}"; Flags: ignoreversion restartreplace
Source: "{#SourceDir}\icon.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs restartreplace

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#InstalledExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#InstalledExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#InstalledExeName}"; Description: "启动{#AppName}"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent
