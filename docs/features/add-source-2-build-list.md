# New feature

## Add source to build list

I want to add a source to an existing `compile-list.json`

### Definition of done
* Add new action `add_source`
* Consider dependencies and build order
* If sources already have status `success`, reset status if the source is affected due to dependencies
* Consider ESP (extended source processing) feature
* Add argument `-c` `--compile-list-dir`
* Consider `--compile-list-dir` if given