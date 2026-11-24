'use strict';

// Add title/date/link metadata only to archive & 随笔 category generation, never to site.posts.
hexo.extend.filter.register('after_init', function () {
  const moment = hexo.extend.helper.get('moment');
  const { Query } = hexo.model('Post');
  const buildPrivateLinks = (config, locals) =>
    (locals.data.private_essays || []).map(item => ({
      title: item.title,
      date: moment(item.date).tz(config.timezone),
      external_url: item.external_url,
      categories: [{ name: '随笔' }]
    }));

  const archiveGenerator = hexo.extend.generator.get('archive');
  if (archiveGenerator) {
    hexo.extend.generator.register('archive', function (locals) {
      const privateLinks = buildPrivateLinks(this.config, locals);
      return archiveGenerator.call(this, {
        ...locals,
        posts: new Query(locals.posts.toArray().concat(privateLinks))
      });
    });
  }

  const categoryGenerator = hexo.extend.generator.get('category');
  if (categoryGenerator) {
    hexo.extend.generator.register('category', function (locals) {
      const privateLinks = buildPrivateLinks(this.config, locals);
      if (!privateLinks.length) return categoryGenerator.call(this, locals);

      const categories = locals.categories.toArray().map(category => {
        if (category.name !== '随笔') return category;
        const posts = new Query(category.posts.toArray().concat(privateLinks));
        return {
          name: category.name,
          path: category.path,
          length: posts.length,
          posts
        };
      });

      return categoryGenerator.call(this, {
        ...locals,
        categories
      });
    });
  }
});
