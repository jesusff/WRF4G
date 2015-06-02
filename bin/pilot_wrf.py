import os
import sys
import time
import socket
import shutil
import logging
import tarfile
import glob
import threading

from os.path              import exists, join, dirname, isfile, basename
from wrf4g.db             import get_session
from wrf4g.core           import Job
from wrf4g.utils.osinfo   import ( get_hostname, os_release, 
                                   cpu_info, mem_info, 
                                   disk_space_check, which )
from wrf4g.utils.command  import exec_cmd_popen as exec_cmd
from wrf4g.utils.archive  import extract
from wrf4g.utils.time     import ( dateiso2datetime, datewrf2datetime, 
                                   datetime2datewrf, datetime2dateiso )
from wrf4g.utils.file     import WRFFile
from wrf4g.utils.namelist import wps2wrf
from wrf4g.config         import load_exp_pkl
from wrf4g.tools.vcplib   import VCPURL, copy_file

__version__  = '2.0.0'
__author__   = 'Carlos Blanco'
__revision__ = "$Id$"


JOB_ERROR = { 
              'EXPERIMENT_FILE'      : 1,
              'LOCAL_PATH'           : 2,
              'LOG_PATH'             : 3,
              'JOB_SHOULD_NOT_RUN'   : 4,
              'COPY_RST_FILE'        : 5,
              'RESTART_MISMATCH'     : 6,
              'COPY_NAMELIST_WPS'    : 7,
              'COPY_REAL_FILE'       : 8,
              'COPY_WPS'             : 9,
              'COPY_BOUND'           : 10,
              'NAMELIST_FAILED'      : 11,
              'PREPROCESSOR_FAILED'  : 12,
              'LINK_GRIB_FAILED'     : 13,
              'UNGRIB_FAILED'        : 14,
              'METGRID_FAILED'       : 15,
              'REAL_FAILED'          : 16,
              'COPY_UPLOAD_WPS'      : 17,
              'WRF_FAILED'           : 18,
              'POSTPROCESSOR_FAILED' : 19,
              'COPY_OUTPUT_FILE'     : 20,
              'COPY_NODES'           : 21,
              }

class JobError( Exception ):
    """Raised when job fails.

    Attributes:
        msg       -- explanation of why job failes
        exit_code -- job exit code
    """

    def __init__(self, msg, exit_code ):
        self.msg       = msg
        self.exit_code = exit_code

    def __str__(self):
        return repr( self.msg )

class JobDB( object ) :

    def __init__(self, job_id) :
        try :
            self.session = get_session()
        except :
            self.session = None
            logging.warning( "Error creating database session" )
        else :
            try :
                self.job = self.session.query( Job ).\
                           filter( Job.gw_job == job_id ).\
                           order_by( Job.id ).all()[-1]
            except :
                self.job = None
                logging.warning( "Error finding job '%s' on the database" % job_id )

    def get_job_status(self):
        if self.session and self.job :
            return self.job.status
        else :
            return 'UNKNOWN'

    def set_job_status(self, status):
        if self.session and self.job :
            self.job.set_status( status )
            try :
                self.session.commit( )
            except :
                logging.warning( "Error updating status '%s' on the database" % status )
                self.session.rollback()

    def get_restart_date(self):
        if self.session and self.job :
            return self.job.chunk.realization.restart

    def has_wps(self):
        if self.session and self.job :
            return self.job.chunk.wps
        else :
            return 0

    def set_wps(self):
        if self.session and self.job :
            self.job.chunk.wps = 1
            try :
                self.session.commit( )
            except :
                logging.warning( "Error updating wps on the database" )
                self.session.rollback()

    def set_restart_date(self, restart_date ):
        if self.session and self.job :
            self.job.chunk.realization.restart = restart_date
            try :
                self.session.commit( )
            except :
                logging.warning( "Error updating restart date '%s' on the database" % restart_date )
                self.session.rollback()

    def set_current_date(self, current_date):
        if self.session and self.job :
            self.job.chunk.realization.current_date = current_date
            try :
                self.session.commit( )
            except :
                logging.warning( "Error updating current date '%s' on the database" % current_date )
                self.session.rollback()

    def set_exit_code(self, exit_code ):
        if self.session and self.job :
            self.job.exitcode = exit_code
            try :
                self.session.commit( )
            except :
                logging.warning( "Error updating exit code" )
                self.session.rollback()

    def close(self) :
        if self.session : 
            self.session.close()


class PilotParams( object ):
    """
    Class to define the parameters of the experiment 
    """
    pilot_wrf           = os.path.abspath( sys.argv[0] )
    root_path           = os.path.dirname( os.path.dirname( pilot_wrf ) )
    exp_conf            = load_exp_pkl( root_path )
    # Find if there is a specific section for this resource
    resource_name  = os.environ.get( 'GW_HOSTNAME' )
    if exp_conf.has_key( resource_name ) :
        resource_exp_conf = exp_conf[ resource_name ]
    else :
        resource_exp_conf = exp_conf[ 'default' ]
    output_path          = resource_exp_conf[ 'output_path' ]
    domain_path          = resource_exp_conf[ 'domain_path' ]
    app_bundles          = resource_exp_conf[ 'app_bundles' ]
    preprocessor         = resource_exp_conf[ 'preprocessor' ]
    postprocessor        = resource_exp_conf[ 'postprocessor' ]
    clean_after_run      = resource_exp_conf[ 'clean_after_run' ]
    extdata_path         = resource_exp_conf[ 'extdata_path' ]
    max_dom              = resource_exp_conf[ 'max_dom' ]
    save_wps             = resource_exp_conf[ 'save_wps' ]
    wrfout_name_end_date = resource_exp_conf[ 'wrfout_name_end_date' ]
    timestep_dxfactor    = resource_exp_conf[ 'timestep_dxfactor' ]
    extdata_vtable       = resource_exp_conf[ 'extdata_vtable' ]
    extdata_interval     = resource_exp_conf[ 'extdata_interval' ]
    real_parallel        = resource_exp_conf[ 'real_parallel' ]
    wrf_parallel         = resource_exp_conf[ 'wrf_parallel' ]
    ppn                  = os.environ.get( 'PPN' )
    np                   = os.environ.get( 'GW_NP' ) 
    job_id               = int( os.environ.get( 'GW_JOB_ID' ) )
    restarted_id         = int( os.environ.get( 'GW_RESTARTED' ) )
    app_bundle_allowed   = ('mpi' , 'wrf', 'nco', 'netcdf' , 'cdo' )
    exp_name             = sys.argv[1]
    rea_name             = sys.argv[2]
    nchunk               = int( sys.argv[3] )
    ##
    # Dates
    ##
    chunk_sdate          = datewrf2datetime( sys.argv[4] )
    chunk_edate          = datewrf2datetime( sys.argv[5] )
    chunk_rdate          = chunk_sdate

    rerun                = int( sys.argv[6] )

    ##
    # Local path
    ##
    local_scp = os.environ.get( "WRF4G_LOCALSCP" )
    if os.environ.get( "WRF4G_LOCALSCP" ) :
        local_path = join( local_scp, "wrf4g_%s_%s" % ( rea_name, nchunk ) )
    else :
        local_path = root_path

    # WRF path variables
    wps_path             = join( local_path, 'WPS')
    wrf_run_path         = join( local_path, 'WRFV3', 'run')

    ###
    # logging configuration
    ###
    log_path             = join( local_path, 'log' )
    log_file             = join( log_path,   'pilot_wrf.log' )

    ##
    # Namelists
    ##
    namelist_wps         = join( wps_path,     'namelist.wps' )
    namelist_input       = join( wrf_run_path, 'namelist.input' )

    ##
    # Remote paths
    ##
    exp_output_path      = join( output_path, exp_name )
    rea_output_path      = join( exp_output_path, rea_name )
    out_rea_output_path  = join( rea_output_path, 'output')
    rst_rea_output_path  = join( rea_output_path, 'restart')
    real_rea_output_path = join( rea_output_path, 'realout')
    log_rea_output_path  = join( rea_output_path, 'log') 

def clean_wrf_files( job_db, params, clean="all" ):
    """
    Postprocess wrfout files and copy files to the output path 
    """
    for patt in [ "wrfout", "wrfrst", "wrfrain", "wrfxtrm", "wrf24hc" ] :
        all_files_patt = glob.glob( join( params.wrf_run_path, patt + '*' ) )
        if clean != 'all' :
            if len( files ) >= 2 :
                files = all_files_patt[ :-1 ]
            else :
                continue
        else :
            files = all_files_patt
        for file in files :
            file_name = basename( file )
            if file_name == "wrfrst_d01_" + datetime2datewrf( params.chunk_rdate ) :
                # Skip the initial restart file
                logging.info( "Skipping initial restart file %s" % file_name )
                continue
            else :
                if "wrfout" in file_name and params.postprocessor :
                    ##
                    # Execute postprocessor
                    ##
                    logging.info( "Running postprocessor.%s" % params.postprocessor )

                    code, output = exec_cmd( "postprocessor.%s %s 2>&1" % (
                                                params.postprocessor, file_name ) )
                    if code :
                        logging.info( output )
                        raise JobError( "'%s' has not copied" % file_name,
                                JOB_ERROR[ 'POSTPROCESSOR_FAILED' ] )
                    # The file will indicate that it has been postprocessed  
                    exec_cmd( 'ncatted -O -a WRF4G_postprocessor,global,o,c,"%s" %s' % 
                                            (params.postprocessor, file) )

                if "wrfrst" and "d01" in file_name :
                    job_db.set_restart_date( WRFFile( file_name ).date_datetime() )

            ##
            # Uploading "wrfout", "wrfrst", "wrfrain", "wrfxtrm", "wrf24hc" files
            ##
            if patt == "wrfout" and params.wrfout_name_end_date == 'yes' :
                code, output = exec_cmd("ncdump -v Times %s" % file )
                mo = re.search("(\d{4}-\d{2}-\d{2}_\d{2}:\d{2}:\d{2})", output.split('\n')[-2] )
                dest_file = WRFFile( file_name, mo.group() ).file_name_out_iso()
            else:
                dest_file = WRFFile( file_name).file_name_iso()
    
            if patt == "wrfrst" :
                dest = join( params.rst_rea_output_path, dest_file )
            else :
                dest = join( params.out_rea_output_path, dest_file )
    
            try :
                logging.info( "Uploading file '%s'" % file )
                os.chmod( file, 0664 )
                copy_file( file, dest )
                try :
                    os.remove( file )     
                except : 
                    pass
            except :
                raise JobError( "'%s' has not copied" % file, JOB_ERROR[ 'COPY_OUTPUT_FILE' ] )

def get_current_date( log_wrf ):
    try :
        try :
            f = open( log_wrf, 'r' )
            log = f.readlines()
            log.reverse()
        finally :
            f.close()
        for line in log :
            if line.find( 'Timing for main: time' ) == 0:
                current_date = datewrf2datetime( line.split()[4] )
                logging.info( "Current date is now '%s'" % current_date )            
                break
        return current_date
    except :
        return None
        
def wrf_monitor( job_db, log_wrf, params ):   
    """
    Monitor wrf.exe processes
    """
    time.sleep( 120 )
    logging.info( "Starting monitor" )
    while True :
        current_date = get_current_date( log_wrf )
        if not current_date :
            current_date = params.chunk_rdate
        job_db.set_current_date( current_date )
        clean_wrf_files( job_db, params, 'closed_files' )
        time.sleep( 60 ) # 1 minute

def main():  
    ##
    # Give all access permissions to the group and allow other users 
    ##
    os.umask( 022 )

    ##
    # Define variables
    ##
    params = PilotParams()
    try :
        os.makedirs( params.log_path )
    except :
        raise JobError( "Error creating the directory '%s' on the worker node" % params.log_path, JOB_ERROR[ 'LOG_PATH'] )

    exit_code = 0
    ##
    # Create a remote tree directory for the realization
    ##
    if not exists( params.local_path ) :
        try :
            os.makedirs( params.local_path )
        except :
            raise JobError( "Error creating the directory '%s' on the worker node" % params.local_path, 
                                JOB_ERROR[ 'LOCAL_PATH'] )

    logging.basicConfig( format='%(asctime)s %(message)s', filename = params.log_file, level = logging.INFO )
    ##
    # DRM4G won't remove root_path if clean_after_run is 1
    ##
    if params.clean_after_run == 'no' :
        logging.info( "Creating a .lock file" )
        f = open( join( params.root_path, '.lock' ), 'w' )
        f.close()

    ##
    # Get database session
    ##
    job_db = JobDB( params.job_id )
    try :
        ##
        # Check if this job should run
        ##
        if job_db.get_job_status() == 'CANCEL' :
            raise JobError( "Error this job should not run", JOB_ERROR[ 'JOB_SHOULD_NOT_RUN'] )

        ##
        # Create a remote tree directory for the realization
        ##
        logging.info( "Creating remote tree directory under '%s'" % params.output_path )
        job_db.set_job_status( 'CREATE_OUTPUT_PATH' )

        for remote_path in [  params.output_path, 
                              params.exp_output_path,
                              params.rea_output_path,
                              params.out_rea_output_path,
                              params.rst_rea_output_path,
                              params.real_rea_output_path,
                              params.log_rea_output_path  ] :
            vcp_dir = VCPURL( remote_path )
            if not vcp_dir.exists() :
                logging.info( "Creating remote directory '%s'" % remote_path )
                vcp_dir.mkdir()

        ##
        # Copy configured files to the ouput path
        ##
        logging.info( "Copy configured files to '%s'" % params.output_path )

        for conf_file in [ "db.conf", "experiment.wrf4g", "experiment.pkl", "namelist.input" ] :
            oring = join( params.root_path, conf_file )
            dest  = join( params.rea_output_path , conf_file )
            try :
                copy_file( oring, dest )
            except :
                logging.warning( "Error copying file '%s' to '%s'" % ( oring, dest ) )

        ##
        # Download and unpack the bundles 
        ##
        logging.info( 'Downloading and unpacking bundles' )
        job_db.set_job_status( 'DOWN_BUNDLES' )

        archives_path = join( params.local_path, 'archives' )
        logging.info( "Creating '%s' directory" % archives_path )
        os.makedirs( archives_path )
        for app_bundle in params.app_bundles.replace(' ','').split('\n') :
            if '|' in app_bundle : 
                bundle_name, bundle_path = app_bundle.split('|')
                if bundle_name in params.app_bundle_allowed :
                    bundle_name, bundle_path = app_bundle.split('|')
                    oiring = bundle_path
                    dest   = join( archives_path, basename( bundle_path ) )
                    logging.info( "Trying to copy '%s'" % oiring )
                    copy_file( oiring, dest )
                    logging.info( "Unpacking '%s' to '%s'" % ( dest, params.local_path ) )
                    if bundle_name == 'mpi' :
                        mpi_config = True
                    extract( dest, to_path = params.root_path )
        wrf4g_files = join( params.root_path, 'wrf4g_files.tar.gz' )
        if isfile( wrf4g_files ) :
            logging.info( "Unpacking '%s'" % wrf4g_files )
            extract( wrf4g_files, to_path = params.root_path )

        ##
        # This is a little bit tricky prepare the pallalel environment.
        ##
        if ( params.real_parallel == 'yes' or params.wrf_parallel == 'yes' ) and \
           ( params.local_path != params.root_path ) :
            logging.info( 'Copy configured files to all worker nodes for parallel execution' )
            code, output = exec_cmd( "mpirun -pernode --wdir cp -r %s %s" % ( params.root_path, params.local_path ) )
            if code :
                logging.info( output )
                raise JobError( "Error copying files to all WNs", JOB_ERROR[ 'COPY_NODES' ] )
        ##
        # Clean archives directory
        ##  
        shutil.rmtree( archives_path )

        ##
        # Setting PATH and LD_LIBRARY_PATH 
        ##
        logging.info( 'Setting PATH and LD_LIBRARY_PATH variables' )

        local_bin_path = join( params.local_path, 'bin' )
        os.environ[ 'PATH' ] = '%s:%s' % ( local_bin_path, os.environ.get( 'PATH' ) )
        os.environ[ 'LD_LIBRARY_PATH' ] = '%s:%s:%s' % ( join( params.local_path, 'lib' ), 
                                                         join( params.local_path, 'lib64' ),
                                                         os.environ.get( 'LD_LIBRARY_PATH' ) )
        os.environ[ 'PYTHONPATH' ] = '%s:%s' % ( join( params.local_path, 'lib', 'python' ), 
                                                 os.environ.get( 'PYTHONPATH' ) )
        if mpi_config :
            os.environ[ 'OPAL_PREFIX' ] = params.root_path

        ##
        # Set bin files execute by the group
        ##
        logging.info( 'Setting bin files execute by the group' )

        for exe_file in os.listdir( local_bin_path ) :
            os.chmod( join( local_bin_path, exe_file ), 0777 )

        ####
        # Obtain information about the WN
        ####
        logging.info( 'Obtaining information about the worker node' )

        # Host info 
        logging.info( 'Host Name = %s' % get_hostname() )

        # OS info
        logging.info( 'Linux release: %s' % os_release() )
                
        # CPU info
        model_name, number_of_cpus = cpu_info()
        logging.info( 'CPU (model) = %s' % model_name )
        logging.info( 'CPU (MHz)   = %d' % number_of_cpus )

        # Memory info
        logging.info( 'Memory (kB)  = %s' % mem_info() )

        # Disk space check
        logging.info( 'DiskSpace (MB) = %d' % disk_space_check( params.root_path ) )

        ##
        # Check the restart date
        ##
        logging.info( 'Checking restart date' )
        rdate = job_db.get_restart_date()
        if not rdate or params.rerun :
            logging.info( "Restart date will be '%s'" % params.chunk_sdate )
            chunk_rerun = ".F."
        elif rdate >= params.chunk_sdate and rdate < params.chunk_edate :
            logging.info( "Restart date will be '%s'" % rdate )
            params.chunk_rdate = rdate
            chunk_rerun = ".T." 
            pattern =  "wrfrst*" + datetime2dateiso( params.chunk_rdate ) + '*'
            for file_name in VCPURL( params.rst_rea_output_path ).ls( pattern ):
                # file will follow the pattern: wrfrst_d01_19900101T000000Z.nc
                orig = join( params.rst_rea_output_path, file_name )
                dest = join( params.wrf_run_path, WRFFile( file_name ).file_name_wrf() )
                try :
                    logging.info( "Downloading file '%s'" % file_name ) 
                    copy_file( orig, dest )
                except :
                    raise JobError( "'%s' has not copied" % file_name, JOB_ERROR[ 'COPY_RST_FILE' ] )
            job_db.set_job_status( 'DOWN_RESTART' )
        elif rdate == params.chunk_edate :
            raise JobError( "Restart file is the end date", JOB_ERROR[ 'RESTART_MISMATCH' ] )
        else :
            raise JobError( "There is a mismatch in the restart date", JOB_ERROR[ 'RESTART_MISMATCH' ] )

        ##
        # Either WPS runs or the boundaries and initial conditions are available
        ##
            
        #Copy namelist.input to wrf_run_path
        shutil.copyfile( join( params.root_path, 'namelist.input' ), params.namelist_input )
        
        if job_db.has_wps() :
            logging.info( "The boundaries and initial conditions are available" )
            orig = join( params.domain_path, basename( params.namelist_wps ) )
            dest = params.namelist_wps
            try :
                logging.info( "Downloading file 'namelist.wps'" )
                copy_file( orig, dest )
            except :
                raise JobError( "'namelist.wps' has not copied", JOB_ERROR[  'COPY_NAMELIST_WPS' ] )
            wps2wrf( params.namelist_wps, params.namelist_input, params.chunk_rdate, 
                        params.chunk_edate, int(params.max_dom), chunk_rerun, params.timestep_dxfactor)
            job_db.set_job_status( 'DOWN_WPS' )
            pattern =  "wrf[lbif]*_d\d\d_" + datetime2dateiso( sdate ) + "*" 
            for file_name in VCPURL( params.real_rea_output_path ).ls( pattern ):
                orig = join( params.real_rea_output_path, file_name )
                # From wrflowinp_d08_ we remove the _ at the end
                dest = join( params.wrf_run_path, WRFFile(file_name).file_name[:-1] )
                try :
                    logging.info( "Downloading file '%s'" % file_name )
                    copy_file( orig, dest )
                except :
                    raise JobError( "'%s' has not copied" % file_name, JOB_ERROR[  'COPY_REAL_FILE' ] )
        else :
            logging.info( "The boundaries and initial conditions are not available" )

            # Change the directory to wps path
            os.chdir( params.wps_path )

            ##
            #  Get geo_em files and namelist.wps
            ##
            logging.info( "Download geo_em files and namelist.wps" )

            for file_name in VCPURL( params.domain_path ).ls( '*' ):
                orig = join( params.domain_path, file_name )
                dest = join( params.wps_path, file_name )
                try :
                    logging.info( "Downloading file '%s'" % file_name )
                    copy_file( orig, dest )
                except :
                    raise JobError( "'%s' has not copied" % file_name,
                            JOB_ERROR[ 'COPY_BOUND' ] )
            job_db.set_job_status( 'DOWN_BOUND' )

            ##
            #  Modify the namelist
            ##
            logging.info( "Modify namelist.wps" )

            cmds = [ "fortnml -of %s -n %s -s start_date %s" % ( params.namelist_wps, 
                                                                 params.max_dom, 
                                                                 datetime2datewrf( params.chunk_sdate ) ), 
                     "fortnml -of %s -n %s -s end_date %s"   % ( params.namelist_wps, 
                                                                 params.max_dom, 
                                                                 datetime2datewrf( params.chunk_edate ) ),
                     "fortnml -of %s -s max_dom %s"          % ( params.namelist_wps, params.max_dom ),
                     "fortnml -of %s -s interval_seconds %s" % ( params.namelist_wps, params.extdata_interval) ]
            for cmd in cmds :
                code, output = exec_cmd( cmd )
                if code :
                    logging.info( output )
                    raise JobError( "Error modifying namelist", JOB_ERROR[ 'NAMELIST_FAILED' ] )
            ##
            # Preprocessor and Ungrib
            ##
            logging.info( "Run preprocessors and ungrib" )

            for vt in params.extdata_vtable.replace(' ', ''). split( ',' ) :
                code, output = exec_cmd( "fortnml -of %s -s prefix@ungrib %s" % ( params.namelist_wps, vt ) )
                if code :
                    logging.info( output )
                    raise JobError( "Error modifying namelist", JOB_ERROR[ 'NAMELIST_FAILED' ] )
                vtable = join( params.wps_path, 'Vtable' )
                if isfile( vtable ) :
                    os.remove( vtable ) 
                # This creates a symbolic link
                os.symlink( join( params.wps_path, 'ungrib', 'Variable_Tables', 'Vtable.%s' % vt ), vtable)

                ##
                # Execute preprocesor
                ##
                logging.info( "Running preprocessor.%s" % params.preprocessor )
              
                code, output = exec_cmd( "preprocessor.%s %s %s %s %s 2>&1" % (
                                            params.preprocessor, datetime2datewrf( params.chunk_rdate ) , 
                                            datetime2datewrf( params.chunk_edate ), params.extdata_path, vt ) )
                logging.info( output )
                if code :
                    raise JobError( "Preprocessor '%s' has failed" % params.preprocessor,
                            JOB_ERROR[ 'PREPROCESSOR_FAILED' ] )

                link_grib     = join( params.wps_path, 'link_grib.sh' ) 
                os.chmod( link_grib, 0777 )
                grb_data_path = join( params.wps_path, 'grbData') 
                code, output  = exec_cmd( "%s %s/" % ( link_grib, grb_data_path ) )
                if code :
                    raise JobError( "Error linking grib files", JOB_ERROR[ 'LINK_GRIB_FAILED' ] )
                ##
                # Run Ungrib
                ##
                logging.info( "Run ungrib" )
                job_db.set_job_status( 'UNGRIB' )

                ungrib_log   = join( params.log_path, 'ungrib_%s.log' % vt )
                ungrib_exe   = which( 'ungrib.exe' )
                if not ungrib_exe :
                    ungrib_exe = join( params.wps_path, 'ungrib', 'ungrib.exe' )
                    os.chmod( ungrib_exe, 0777 )      
                code, output = exec_cmd( "%s > %s" % ( ungrib_exe, ungrib_log) )
                if code or not 'Successful completion' in open( ungrib_log, 'r' ).read() : 
                    raise JobError( "'%s' has failed" % ungrib_exe,
                                JOB_ERROR[ 'UNGRIB_FAILED' ] )
                shutil.rmtree( grb_data_path )
                grib_files = glob.glob( join( params.wps_path, 'GRIBFILE.*' ) )
                for grib_file in grib_files :
                    os.remove( grib_file )
          
            ##
            #  Update namelist.wps 
            ##
            logging.info( "Update namelist for metgrid" )

            exec_cmd( "fortnml -of %s -s fg_name@metgrid %s" % ( params.namelist_wps, params.extdata_vtable ) )
            for var_to_del in [ 'opt_output_from_metgrid_path',
                                'opt_output_from_geogrid_path',
                                'opt_metgrid_tbl_path',
                                'opt_geogrid_tbl_path' ] :
                code, output = exec_cmd( "fortnml -of %s -d %s" % ( params.namelist_wps, var_to_del ) )
                if code :
                    logging.info( output )
                    raise JobError( "Error modifying namelist", JOB_ERROR[ 'NAMELIST_FAILED' ] )
          
            ##
            # Run Metgrid
            ##
            logging.info( "Run metgrid" )

            metgrid_log = join( params.log_path, 'metgrid.log' )
            metgrid_exe = which( 'metgrid.exe' )
            if not metgrid_exe :
                metgrid_exe = join( params.wps_path, 'metgrid', 'metgrid.exe' )
                os.chmod( metgrid_exe, 0777 )
            code, output = exec_cmd( "%s > %s" % ( metgrid_exe, metgrid_log ) )
            if code or not 'Successful completion' in open( metgrid_log, 'r' ).read() :
                raise JobError( "'%s' has failed" % metgrid_exe, JOB_ERROR[ 'METGRID_FAILED' ] )
            job_db.set_job_status( 'METGRID' )

            ##
            # Run real
            ##

            # Change the directory to wrf run path
            os.chdir( params.wrf_run_path )
            
            logging.info( "Run real" )
            job_db.set_job_status( 'REAL' )
            # Create a sumbolic link to run real
            met_files = glob.glob( join( params.wps_path, 'met_em.d*' ) )
            for met_file in met_files :
                os.symlink( met_file , join( params.wrf_run_path, basename(met_file) ) )        
            wps2wrf( params.namelist_wps, params.namelist_input, params.chunk_rdate,
                        params.chunk_edate, int( params.max_dom) , chunk_rerun, params.timestep_dxfactor)

            real_exe = which( 'real.exe' )
            if real_exe == 'real.exe' :
                os.chmod( real_exe, 0777 )
                real_exe = './' + real_exe
            if params.real_parallel == 'yes' :
                real_log = join( params.log_path, 'rsl.out.0000' )
                npernode = "-npernode %s" % params.ppn if params.ppn else '' 
                if params.local_path == params.root_path :
                    cmd = "mpirun -np %s %s %s" % ( params.np, npernode, real_exe ) 
                else :
                    cmd = "mpirun -np %s %s --preload-files namelist.input --preload-files-dest-dir %s %s" % (
                           params.np, npernode, params.wrf_run_path, real_exe ) 
                code, output = exec_cmd( cmd ) 
                if isfile( real_log ) :
                    real_rsl_path = join( params.log_path, 'rsl_real' ) 
                    os.mkdir( real_rsl_path )
                    rsl_files = glob.glob( join( params.wrf_run_path, 'rsl.*' ) )
                    for rsl_file in rsl_files :
                        shutil.copyfile( rsl_file, join( real_rsl_path, basename( rsl_file ) ) )  
            else :
                real_log = join( params.log_path, 'real.log' )
                code, output = exec_cmd( "%s > %s" % ( real_exe, real_log ) )
            if code or not 'SUCCESS COMPLETE' in open( real_log, 'r' ).read() :
                raise JobError( "'%s' has failed" % real_exe, JOB_ERROR[ 'REAL_FAILED' ] )
            
            ##
            # Check if wps files has to be storaged 
            ##   
            if params.save_wps == 'yes' :
                logging.info( "Saving wps" )
                job_db.set_job_status( 'UPLOAD_WPS' )
                # If the files are WPS, add the date to the name. Three files have to be uploaded: wrfinput_d0?,wrfbdy_d0? and wrflowinp_d0?
                # The command: $ upload_file wps     1990-01-01_00:00:00
                # will create in the repositore three files with the following format: wrfinput_d01_19900101T000000Z
                suffix = "_" + datetime2dateiso( params.chunk_rdate )+ ".nc"
                for wps_file in VCPURL( params.wps_path ).ls("wrf[lbif]*_d\d\d") :
                    oiring = wps_file
                    dest   = join( params.real_rea_output_path, basename( wps_file) , suffix )
                    try:
                        logging.info( "Uploading '%s' file" % oiring )
                        os.chmod( oiring, 0664 ) 
                        copy_file( oiring, dest )
                    except :
                        raise JobError( "'%s' has not copied" % oiring, JOB_ERROR[  'COPY_UPLOAD_WPS' ] )
                job_db.set_wps()
        
        # Change the directory to wrf run path
        os.chdir( params.wrf_run_path )

        ##
        # Start a thread to monitor wrf 
        ##
        if params.wrf_parallel == 'yes' :
            log_wrf = join( params.wrf_run_path, 'rsl.out.0000' )
        else :
            log_wrf = join( params.log_path, 'wrf.log' )
        worker = threading.Thread( target = wrf_monitor, args = ( job_db, log_wrf, params ) )
        worker.setDaemon(True)
        worker.start()

        ##
        # Run wrf
        ##
        logging.info( "Run wrf" )
        job_db.set_job_status( 'WRF' )

        wrf_exe = which( 'wrf.exe' )
        if wrf_exe == 'wrf.exe' :
            os.chmod( wrf_exe, 0777 )
            wrf_exe = './' + wrf_exe
        if params.wrf_parallel == 'yes' :
            npernode = "-npernode %s" % params.ppn if params.ppn else ''
            if params.local_path == params.root_path :
                cmd = "mpirun -np %s %s %s" % ( params.np, npernode, wrf_exe )                       
            else :
                cmd = "mpirun -np %s %s --preload-files namelist.input --preload-files-dest-dir %s %s" % (
                            params.np, npernode, params.wrf_run_path, wrf_exe )
            code, output = exec_cmd( cmd )
            if isfile( log_wrf ) :
                wrf_rsl_path = join( params.log_path, 'rsl_wrf' ) 
                os.mkdir( wrf_rsl_path )
                rsl_files = glob.glob( join( params.wrf_run_path, 'rsl.*' ) )
                for rsl_file in rsl_files :
                    shutil.copyfile( rsl_file, join( wrf_rsl_path, basename( rsl_file ) ) )  
        else :
            code, output = exec_cmd( "%s > %s" % ( wrf_exe, log_wrf ) )
        if code or not 'SUCCESS COMPLETE' in open( log_wrf, 'r' ).read() :
            raise JobError( "'%s' has failed" % wrf_exe,
                    JOB_ERROR[ 'WRF_FAILED' ] )
        ##
        # Update current date
        ##
        current_date = get_current_date( log_wrf )
        if not current_date :
            current_date = params.chunk_rdate
        job_db.set_current_date( current_date )

        ##
        # Save all files
        ##    
        clean_wrf_files( job_db, params, 'all' )

        ##
        # Update the status
        ##
        job_db.set_job_status( 'FINISHED' )
    except JobError, err :
        logging.error( err.msg )
        job_db.set_job_status( 'FAILED' )
        exit_code = err.exit_code
    finally :
        ##
        # Create a log bundle 
        ##
        os.chdir( params.local_path )
        log_tar = "log_%d_%d.tar.gz" % ( params.nchunk, params.job_id )
        try :
            tar = tarfile.open( log_tar , "w:gz" )
            tar.add( 'log' )
        finally :
            tar.close()
        # Local copy that will use as outsandbox
        if params.root_path != params.local_path :
            oring = join( params.local_path, log_tar )
            dest  = join( params.root_path, log_tar ) 
            shutil.copyfile( oring, dest )
        # Copy to repository
        oring = join( params.root_path, log_tar )
        dest  = join( params.log_rea_output_path, log_tar )
        copy_file( oring, dest )

        ##
        # Close the connection with the database
        ##
        job_db.set_exit_code( exit_code )
        job_db.close()
        sys.exit( exit_code )

if __name__ == '__main__':
    try :
        main()
    except JobError, err :
        try :
            logging.error( err.msg )
        except :
            sys.stderr.write( err.msg )
        sys.exit( err.exit_code )
    except Exception, err :
        sys.stderr.write( str( err ) )
        sys.exit( -1 )
