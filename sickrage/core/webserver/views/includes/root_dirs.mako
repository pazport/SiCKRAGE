<%
    import sickrage

    if sickrage.app.config.root_dirs:
        backend_pieces = sickrage.app.config.root_dirs.split('|')
        backend_default = 'rd-' + backend_pieces[0]
        backend_dirs = backend_pieces[1:]
    else:
        backend_default = ''
        backend_dirs = []
%>

<div class="row">
    <div class="col-md-12">
        <span id="sampleRootDir"></span>
        <input type="hidden" id="whichDefaultRootDir" value="${backend_default}"/>
        <div class="rootdir-selectbox">
            <div class="input-group">
                <div class="input-group-prepend">
                    <span class="input-group-text">
                        <span class="fas fa-folder-open"></span>
                    </span>
                </div>
                <select name="rootDir" id="rootDirs" size="6" class="form-control"
                        title="${_('Root Directories')}">
                    % for cur_dir in backend_dirs:
                        <option value="${cur_dir}">${cur_dir}</option>
                    % endfor
                </select>
            </div>
        </div>
    </div>
</div>
<div class="row">
    <div class="col-md-12 mt-1">
        <div id="rootDirsControls" class="rootdir-controls">
            <input class="sickrage-btn m-1" type="button" id="addRootDir" value="${_('New')}"/>
            <input class="sickrage-btn m-1" type="button" id="editRootDir" value="${_('Edit')}"/>
            <input class="sickrage-btn m-1" type="button" id="deleteRootDir" value="${_('Delete')}"/>
            <input class="sickrage-btn m-1" type="button" id="defaultRootDir" value="${_('Set as Default *')}"/>
        </div>
        <input type="text" style="display: none" id="rootDirText" autocapitalize="off" title=""/>
    </div>
</div>

