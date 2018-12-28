#!/usr/bin/perl

# Copyright 2016 Christian Fenzl, christiantf@gmx.at
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


##########################################################################
# Modules
##########################################################################

use POSIX 'strftime';
use CGI::Carp qw(fatalsToBrowser);
use CGI qw/:standard/;
use Config::Simple;
use File::HomeDir;
use Cwd 'abs_path';
use warnings;
use strict;

no strict "refs"; # we need it for template system

##########################################################################
# Variables
##########################################################################

our $cfg;
our $phrase;
our $namef;
our $value;
our %query;
our $lang;
our $template_title;
our $help;
our @help;
our $helptext;
our $helplink;
our $installfolder;
our $languagefile;
our $version;
our $error;
our $saveformdata=0;
our $output;

my  $home = File::HomeDir->my_home;
our $debug=1;
our $languagefileplugin;
our $plglang;

our $header_already_sent=0;

our $pluginname;

our $cfgfilename;
our $cfgversion=0;
our $cfg_version;

our $awui_port;
our $awui_enabled;
our $awui_debug;
our $awuilink;
our $awui_debug_enabled;
our $enabled;
our $awui_is_running;
our $awuirunning;

my $logname;
my $loghandle;
my $logmessage;


##########################################################################
# Read Settings
##########################################################################

# Version of this script
$version = "0.1.3";

# Figure out in which subfolder we are installed
$pluginname = abs_path($0);
$pluginname =~ s/(.*)\/(.*)\/(.*)$/$2/g;

# Read global settings

$cfg             = new Config::Simple("$home/config/system/general.cfg");
$installfolder   = $cfg->param("BASE.INSTALLFOLDER");
$lang            = $cfg->param("BASE.LANG");

# Initialize logfile
if ($debug) {
	$logname = "$installfolder/log/plugins/$pluginname/index.log";
	open ($loghandle, '>>' , $logname); # or warn "Cannot open logfile for writing (Permission?) - Continuing without log\n";
	chmod (0666, $loghandle); # or warn "Cannot change logfile permissions\n";	
}

# Read plugin settings
$cfgfilename = "$installfolder/config/plugins/$pluginname/alsamixer.cfg";
tolog("INFORMATION", "Reading Plugin config $cfgfilename");
if (-e $cfgfilename) {
	tolog("INFORMATION", "Plugin config existing - loading");
	$cfg = new Config::Simple($cfgfilename);
}
unless (-e $cfgfilename) {
	tolog("INFORMATION", "Plugin config NOT existing - creating");
	$cfg = new Config::Simple(syntax=>'ini');
	$cfg->param("Main.ConfigVersion", 1);
	$cfg->write($cfgfilename);
}
	

#########################################################################
# Parameter
#########################################################################

# For Debugging with level 3 
sub apache()
{
  if ($debug eq 3)
  {
		if ($header_already_sent eq 0) {$header_already_sent=1; print header();}
		my $debug_message = shift;
		# Print to Browser 
		print $debug_message."<br>\n";
		# Write in Apache Error-Log 
		print STDERR $debug_message."\n";
	}
	return();
}

# Everything from URL
foreach (split(/&/,$ENV{'QUERY_STRING'}))
{
  ($namef,$value) = split(/=/,$_,2);
  $namef =~ tr/+/ /;
  $namef =~ s/%([a-fA-F0-9][a-fA-F0-9])/pack("C", hex($1))/eg;
  $value =~ tr/+/ /;
  $value =~ s/%([a-fA-F0-9][a-fA-F0-9])/pack("C", hex($1))/eg;
  $query{$namef} = $value;
}

# Set parameters coming in - get over post
# Don't know why this is so complicated...
	if ( !$query{'saveformdata'} ) { if ( param('saveformdata') ) { $saveformdata = quotemeta(param('saveformdata')); } else { $saveformdata = 0;      } } else { $saveformdata = quotemeta($query{'saveformdata'}); }
	if ( !$query{'lang'} )         { if ( param('lang')         ) { $lang         = quotemeta(param('lang'));         } else { $lang         = "de";   } } else { $lang         = quotemeta($query{'lang'});         }

# Clean up saveformdata variable
	$saveformdata =~ tr/0-1//cd; $saveformdata = substr($saveformdata,0,1);

# Init Language
	# Clean up lang variable
	$lang         =~ tr/a-z//cd; $lang         = substr($lang,0,2);
# If there's no language phrases file for choosed language, use german as default
	if (!-e "$installfolder/templates/system/$lang/language.dat") 
	{
  		$lang = "de";
	}
# Read LoxBerry system translations / phrases
	$languagefile 			= "$installfolder/templates/system/$lang/language.dat";
	$phrase 				= new Config::Simple($languagefile);
	
# Read Plugin transations
# Read English language as default
# Missing phrases in foreign language will fall back to English	
	
	$languagefileplugin 	= "$installfolder/templates/plugins/$pluginname/en/language.txt";
	$plglang = new Config::Simple($languagefileplugin);
	$plglang->import_names('T');

#	$lang = 'en'; # DEBUG
	
# Read foreign language if exists and not English
	$languagefileplugin = "$installfolder/templates/plugins/$pluginname/$lang/language.txt";
	 if ((-e $languagefileplugin) and ($lang ne 'en')) {
		# Now overwrite phrase variables with user language
		$plglang = new Config::Simple($languagefileplugin);
		$plglang->import_names('T');
	}
	
#	$lang = 'de'; # DEBUG
	
##########################################################################
# Main program
##########################################################################

	if ($saveformdata) 
	{
		tolog("DEBUG", "save triggered - save, refresh form");
		&save;
		&form;
	}
	else 
	{
	  tolog("DEBUG", "form triggered - load form");
	  &form;
	}
	exit;

#####################################################
# 
# Subroutines
#
#####################################################

#####################################################
# Form-Sub
#####################################################

	sub form 
	{
		# Filter
		# $debug     = quotemeta($debug);
		tolog("INFORMATION", "save triggered - save, refresh form");
							
		# Prepare form defaults

		# Read the Main config file section
		$cfgversion = $cfg->param("Main.ConfigVersion");
		$awui_enabled = $cfg->param("Main.enabled");
		$awui_port = $cfg->param("Main.port");

		$awui_debug = $cfg->param("Main.debug");
		if (($awui_debug eq "True") || ($awui_debug eq "Yes")) {
			$awui_debug_enabled = 'checked';
			# $debug = 1;
		} else {
			$awui_debug_enabled = '';
			# $debug = 0;
		}

		# If enabled or port are not defined yet, set default values
		if (( $awui_enabled eq "" ) || ( $awui_enabled eq "true" ) || ( $awui_enabled eq "yes" ))  {
			$awui_enabled = "true";
			$enabled = "checked";
		}  
		
		# Generate link to ALSA Web UI 
		if ($enabled eq "checked") {
			$awuilink = "<a target=\"_blank\" href=\"http://$ENV{'HTTP_HOST'}:$awui_port/\">ALSA Mixer Webinterface</a>";
		}
		
		# Set default port if port is empty
		if ( $awui_port eq "" ) {
			$awui_port = 19579;
		}
		
		# Query if Mixer-WebUI is running
		# $awui_is_running = `ps ax | grep alsamixer-webui | grep -v grep | awk '{print $1}'`;
		$awui_is_running = `pgrep -f alsamixer-webui.py`;
		if ($awui_is_running) {
			$awuirunning = "$T::BASIC_AWUI_SERVICE_RUNNING";
		} else {
			$awuirunning = "$T::BASIC_AWUI_SERVICE_NOT_RUNNING";
		}
		
		if ( !$header_already_sent ) { print "Content-Type: text/html\n\n"; }
		
		$template_title = "ALSA Tools Webinterface";
		
		# Print Template
		&lbheader;
		open(F,"$installfolder/templates/plugins/$pluginname/multi/settings.html") || die "Missing template plugins/$pluginname/multi/settings.html";
		  while (<F>) 
		  {
		    $_ =~ s/<!--\$(.*?)-->/${$1}/g;
		    $_ =~ s/<!--\$(.*?)-->/${$1}/g;
		    print $_;
		  }
		close(F);
		&footer;
		exit;
	}

#####################################################
# Save-Sub
#####################################################

	sub save 
	{
		
		# Read global plugin values from form and write to config
		
		$cfg_version 		= param('ConfigVersion');
		$awui_enabled 		= param("Enabled");
		$awui_port 			= param("Port");
		$awui_debug			= param('debug');
		
		$cfg->param("Main.ConfigVersion", $cfg_version);
		$cfg->param("Main.port", $awui_port);
		if ($awui_enabled) {
			$cfg->param("Main.enabled", "true");
		} else {
			$cfg->param("Main.enabled", "false");
		}
		if ($awui_debug) {
			$cfg->param("Main.debug", "Yes");
		} else {
			$cfg->param("Main.debug", "False");
		}
		
		# Run through instance table
		
		$cfg->save();
		
		# (Re-Start service)
		my $restart_command = "sudo $installfolder/bin/plugins/$pluginname/startstop-daemon.sh";
		print STDERR $restart_command . "\n";
		qx { $restart_command };
		
		
	}


#####################################################
# Error-Sub
#####################################################

	sub error 
	{
		$template_title = $phrase->param("TXT0000") . " - " . $phrase->param("TXT0028");
		if ( !$header_already_sent ) { print "Content-Type: text/html\n\n"; }
		&lbheader;
		open(F,"$installfolder/templates/system/$lang/error.html") || die "Missing template system/$lang/error.html";
    while (<F>) 
    {
      $_ =~ s/<!--\$(.*?)-->/${$1}/g;
      print $_;
    }
		close(F);
		&footer;
		exit;
	}

#####################################################
# Page-Header-Sub
#####################################################

	sub lbheader 
	{
		 # Create Help page
	  $helplink = "http://www.loxwiki.eu:80/x/_4Cm";
	  
	# Read Plugin Help transations
	# Read English language as default
	# Missing phrases in foreign language will fall back to English	
	
	$languagefileplugin	= "$installfolder/templates/plugins/$pluginname/en/help.txt";
	$plglang = new Config::Simple($languagefileplugin);
	$plglang->import_names('T');

	# Read foreign language if exists and not English
	$languagefileplugin = "$installfolder/templates/plugins/$pluginname/$lang/help.txt";
	 if ((-e $languagefileplugin) and ($lang ne 'en')) {
		# Now overwrite phrase variables with user language
		$plglang = new Config::Simple($languagefileplugin);
		$plglang->import_names('T');
	}
	  
	# Parse help template
	open(F,"$installfolder/templates/plugins/$pluginname/multi/help.html") || die "Missing template plugins/$pluginname/multi/help.html";
		while (<F>) {
			$_ =~ s/<!--\$(.*?)-->/${$1}/g;
		    $helptext = $helptext . $_;
		}
	close(F);
	open(F,"$installfolder/templates/system/$lang/header.html") || die "Missing template system/$lang/header.html";
	while (<F>) 
		{
	      $_ =~ s/<!--\$(.*?)-->/${$1}/g;
	      print $_;
	    }
	  close(F);
	}

#####################################################
# Footer
#####################################################

	sub footer 
	{
	  open(F,"$installfolder/templates/system/$lang/footer.html") || die "Missing template system/$lang/footer.html";
	    while (<F>) 
	    {
	      $_ =~ s/<!--\$(.*?)-->/${$1}/g;
	      print $_;
	    }
	  close(F);
	}


#####################################################
# Strings trimmen
#####################################################

sub trim { my $s = shift; $s =~ s/^\s+|\s+$//g; return $s };


#####################################################
# Logging
#####################################################

sub tolog {
  # print strftime("%Y-%m-%d %H:%M:%S", localtime(time)) . " $_[0]: $_[1]\n";
  if ($debug) {
	if ($loghandle) {
		print $loghandle strftime("%Y-%m-%d %H:%M:%S", localtime(time)) . " $_[0]: $_[1]\n";
	}
  }
}
