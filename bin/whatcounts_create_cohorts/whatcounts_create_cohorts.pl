#!/usr/bin/env perl

use Mojolicious::Lite;
use Mojo::Util qw( url_escape );
use Mojo::JSON qw(decode_json encode_json);
use IO::All;
use Text::CSV;
use DateTime;
use Try::Tiny;
use Data::Dumper;
use FindBin '$Bin';
use Readonly;
use utf8::all;
use autodie;
use Data::Dumper;

# Read API key and forum name from a config file using autodie
my $config_file < io "$Bin/conf/whatcounts_create_cohorts.json";

my $conf = decode_json $config_file;

# Set any constants
Readonly my $API => $conf->{'wc_api_url'};

my $dt = DateTime->now;
my $yesterday = $dt->clone->subtract( days => 1 );

my $ymd_today     = $dt->mdy( '/' );
my $ymd_yesterday = $yesterday->mdy( '/' );

my $args = {
    r       => $conf->{'wc_realm'},
    p       => $conf->{'wc_password'},
    list_id => $conf->{'wc_listid'},
    c       => 'rpt_sub_by_update_datetime',
    start_datetime => $ymd_yesterday,    # Always yesterday
    end_datetime   => $ymd_today,        # Always today
    output_format  => 'csv',
    headers        => '1'
};

# Make request to WhatCounts API, check response status
my $ua = Mojo::UserAgent->new;
my $result;
my $errors;
my $r = $ua->get( $API => form => $args );
if ( my $res = $r->success ) {
    $result = $res->body;
    $result > io( 'subscribers.csv' );

    # Read the CSV
    my $subscriber_hr = csv_read();

    # Check the created date value for yesterday's date
    my $subs_to_update = subscriber_check( $subscriber_hr );

    # Update the record and add a random between 0-3
    my $results = subscriber_update( $subs_to_update );
}
else {
    my ( $err, $code ) = $r->error;
    $errors = $code ? "$code response: $err" : "Connection error: $err";
    say $errors;
}

sub csv_read {
    my @rows;
    my $csv = Text::CSV->new( { binary => 1 } ) # should set binary attribute.
        or die "Cannot use CSV: " . Text::CSV->error_diag();

    open my $fh, "<:encoding(utf8)", "subscribers.csv"
        or die "subscribers.csv: $!";
    my $hr;
    $csv->column_names( $csv->getline( $fh ) );
    $hr = $csv->getline_hr_all( $fh );
    return $hr;
}

sub subscriber_check {
    my $subscribers = shift;
    my @subs_to_update;
    for my $sub ( @$subscribers ) {
        # We're going to sneakily use the Fax field to indicate records that
        # have been imported, so they are not assigned a cohort
        next if $sub->{'fax'} eq 'cohort_skip';
        # Only update subscribers with a created date that matches their update date
        # i.e., new subscribers, not existing updates from Recurly sync, etc.
        if ( $sub->{'created_date'} =~ $ymd_yesterday ) {
            push @subs_to_update, $sub;
        }
    }
    return \@subs_to_update;
}

sub subscriber_update {
    my $subs_to_update = shift;
    my @results;
    for my $sub ( @$subs_to_update ) {
        $sub->{'custom_cohort'} = int( rand( 4 ) );
        my $res = _post_to_whatcounts( $sub );
        push @results, $res;
    }
    return \@results;
}

sub _post_to_whatcounts {
    my $subscriber = shift;
    my $email  = $subscriber->{'email'};
    my $cohort = $subscriber->{'custom_cohort'};
    my $id     = $subscriber->{'subscriber_id'};
    my $args   = {
        r       => $conf->{'wc_realm'},
        p       => $conf->{'wc_password'},
        list_id => $conf->{'wc_listid'},
        c       => 'update',
        data    => "email,custom_cohort^$email,$cohort"
    };
    my $result;
    my $tx = $ua->get( $API => form => $args );

    if ( my $res = $tx->success ) {
        $result = $res->body;
    }
    else {
        my ( $err, $code ) = $tx->error;
        $result = $code ? "$code response: $err" : "Connection error: $err";
    }
    return $result;
}
