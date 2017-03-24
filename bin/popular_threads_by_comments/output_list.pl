#!/usr/bin/env perl

use Mojo::Loader;
use Mojo::JSON;
use Mojo::UserAgent;
use Mojo::Template;
use Mojo::Util qw/ encode slurp spurt /;
use FindBin '$Bin';
use Readonly;
use utf8::all;
use autodie;
use Data::Dumper;

# Read API key and forum name from a config file using autodie
my $config_file = slurp "$Bin/conf/popular_threads_by_comments.json";

my $json = Mojo::JSON->new;
my $conf = $json->decode( $config_file );

# Read the output path and filename from STDIN
my $output_file = shift @ARGV;
die 'No output file specified' unless $output_file;

# Set any constants
Readonly my $API      => $conf->{'api_url'};
Readonly my $RESOURCE => '/threads/listPopular.json';
Readonly my $URL      => $API . $RESOURCE;

# Set arguments for the API call: api_key, forum, limit, etc.
my $args = { 
    api_key => $conf->{'api_key'},
    forum   => $conf->{'forum'},
    limit   => '5'
};

# Make request to Disqus API, check response status
# If the status is okay, then decode the results from JSON
my $ua   = Mojo::UserAgent->new;
my $res = $ua->get( $URL => form => $args )->res->body;
my $data = $json->decode( $res );

# Store the array data that we're after
my $threads = $data->{'response'};

# Render the data in a template, if we have new data
if ( $threads ) {
    my $loader   = Mojo::Loader->new;
    my $template = $loader->data( __PACKAGE__, 'list' );
    my $mt       = Mojo::Template->new;
    my $output_html = $mt->render( $template, $threads );
    $output_html = encode 'UTF-8', $output_html;

    # Write the template output to a filehandle
    spurt $output_html, $output_file;
};

__DATA__
@@ list
% my ($data) = @_;
<ul id="most_commented">
% for my $thread ( @$data ) {
    <li><a href="<%= $thread->{'link'} %>"><%= $thread->{'title'} %></a> <span>(<%= $thread->{'posts'} %> comments)</span></li>
% }
</ul>
